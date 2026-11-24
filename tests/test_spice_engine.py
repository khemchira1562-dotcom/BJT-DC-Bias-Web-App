"""Unit tests for the Lab 04 ngspice adapter.

These tests never call ngspice. A fake runner supplies real-format log text so
parsing, validation and error paths can be checked on any machine.
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import spice_engine
from spice_engine import (
    DEFAULT_MODEL,
    EngineUnavailable,
    InputError,
    SimulationError,
    build_netlist,
    parse_spice_inputs,
    run_simulation,
)
from charts import bode_svg, waveform_svg


BASE = {
    "analysis": "dc",
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "rl": "10",
    "cin_uf": "10",
    "cout_uf": "10",
    "amplitude_mv": "10",
    "frequency_khz": "1",
    "model": DEFAULT_MODEL,
    "fmin_hz": "10",
    "fmax_hz": "1000000",
    "tran_stop_ms": "5",
}

OP_LOG = """Circuit: Lab 04 CE reference

--- Operating Point ---

V(vcc):\t12.000000 voltage
V(base):\t1.942100 voltage
V(collector):\t9.294300 voltage
V(emitter):\t1.242100 voltage
"""

OP_TABLE_LOG = """Circuit: * Lab 04 CE reference

Doing analysis at TEMP = 27.000000 and TNOM = 27.000000

No. of Data Rows : 1
\tNode                                  Voltage
\t----                                  -------
\tvout                             0.000000e+00
\tvin                              0.000000e+00
\temitter                          1.175805e+00
\tcollector                        9.438841e+00
\tbase                             1.954004e+00
\tvcc                              1.200000e+01

\tSource\tCurrent
\t------\t-------

\tvcc#branch                      -1.26462e-03
"""

# Real ngspice-47 batch mode prints vp() in radians (-170 deg -> -2.96706).
AC_LOG = """Circuit: Lab 04 CE reference

Index   frequency   vm(vin)    vm(vout)   vp(vin)    vp(vout)
0       1.00000e+01 1.00000e-02 5.00000e-02 0.00000e+00 -2.96705973e+00
1       1.00000e+02 1.00000e-02 4.00000e-02 0.00000e+00 -3.05432619e+00
2       1.00000e+03 1.00000e-02 2.00000e-01 0.00000e+00 -3.12413936e+00
"""

AC_SPLIT_LOG = """Circuit: Lab 04 CE reference

Index   frequency   vm(vin)    vm(vout)
0       1.00000e+01 1.00000e-02 5.00000e-02
1       1.00000e+03 1.00000e-02 2.00000e-01

Index   frequency   vp(vin)    vp(vout)
0       1.00000e+01 0.00000e+00 -2.96705973e+00
1       1.00000e+03 0.00000e+00 -3.12413936e+00
"""

TRAN_LOG = """Circuit: Lab 04 CE reference

Index   time        v(vin)      v(vout)
0       0.00000e+00 0.00000e+00 0.00000e+00
1       1.00000e-05 1.00000e-02 -5.00000e-02
2       2.00000e-05 -1.00000e-02 5.00000e-02
3       3.00000e-05 1.00000e-02 -5.00000e-02
4       4.00000e-05 -1.00000e-02 5.00000e-02
5       5.00000e-05 1.00000e-02 -5.00000e-02
"""


def runner_for(log_text: str, returncode: int = 0):
    """Fake runner writing the log file that the adapter expects to read."""

    def run(cmd: list[str], cwd: Path, timeout: int) -> tuple[int, str, str]:
        (cwd / "run.log").write_text(log_text, encoding="utf-8")
        return returncode, log_text, ""

    return run


class ValidationTests(unittest.TestCase):
    def test_accepts_reference_fixture(self) -> None:
        inputs = parse_spice_inputs(BASE)
        self.assertEqual(inputs.analysis, "dc")
        self.assertEqual(inputs.model_name, "QNPN_LAB04")

    def test_unknown_analysis_is_error(self) -> None:
        with self.assertRaises(InputError):
            parse_spice_inputs({**BASE, "analysis": "noise"})

    def test_zero_resistance_is_error(self) -> None:
        with self.assertRaises(InputError):
            parse_spice_inputs({**BASE, "re": "0"})

    def test_bad_frequency_range_is_error(self) -> None:
        with self.assertRaises(InputError):
            parse_spice_inputs({**BASE, "fmax_hz": "5"})

    def test_model_injection_is_rejected(self) -> None:
        with self.assertRaises(InputError):
            parse_spice_inputs({**BASE, "model": ".model x npn\n.op"})

    def test_non_numeric_is_error(self) -> None:
        with self.assertRaises(InputError):
            parse_spice_inputs({**BASE, "vcc": "abc"})


class NetlistTests(unittest.TestCase):
    def test_dc_netlist_contains_op_and_no_print(self) -> None:
        netlist = build_netlist(parse_spice_inputs(BASE))
        self.assertIn(".op", netlist)
        self.assertNotIn(".print", netlist)
        self.assertIn("R2 base 0 22k", netlist)
        self.assertIn("RL vout 0 10k", netlist)

    def test_ac_netlist_has_dec_sweep_and_gain_columns(self) -> None:
        netlist = build_netlist(
            parse_spice_inputs({**BASE, "analysis": "ac"})
        )
        self.assertIn(".ac dec 20 10 1e+06", netlist)
        self.assertIn("vm(vin) vm(vout) vp(vin) vp(vout)", netlist)

    def test_command_uses_batch_mode_without_rawfile_flag(self) -> None:
        calls: list[list[str]] = []

        def fake_run(cmd: list[str], cwd: Path, timeout: int, **kwargs):
            calls.append(cmd)
            (Path(cwd) / "run.log").write_text(OP_LOG, encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, OP_LOG, "")

        with patch.object(spice_engine.subprocess, "run", side_effect=fake_run):
            run_simulation(BASE, executable="ngspice", runner=None)
        self.assertIn("-b", calls[0])
        self.assertIn("-o", calls[0])
        self.assertNotIn("-r", calls[0])

    def test_console_engine_is_preferred_on_windows(self) -> None:
        def fake_which(name: str) -> str | None:
            return r"C:\Spice64\bin\ngspice_con.exe" if name == "ngspice_con" else None

        def fake_process(cmd: list[str], cwd: str, **kwargs):
            (Path(cwd) / "run.log").write_text(OP_LOG, encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, OP_LOG, "")

        with patch.object(spice_engine.shutil, "which", side_effect=fake_which):
            with patch.object(spice_engine.subprocess, "run", side_effect=fake_process):
                result = run_simulation(BASE)
        self.assertEqual(result["engine"], "ngspice")
        self.assertEqual(result["engine_status"], "success")


class ParsingTests(unittest.TestCase):
    def test_dc_values_come_from_log(self) -> None:
        result = run_simulation(BASE, executable="ngspice", runner=runner_for(OP_LOG))
        self.assertAlmostEqual(float(result["vb_v"]), 1.9421, places=4)
        self.assertAlmostEqual(float(result["ic_ma"]), (12.0 - 9.2943) / 2.2, places=4)
        self.assertEqual(result["engine"], "ngspice")
        self.assertEqual(result["engine_status"], "success")

    def test_dc_parser_reads_real_ngspice_batch_table(self) -> None:
        result = run_simulation(
            BASE, executable="ngspice", runner=runner_for(OP_TABLE_LOG)
        )
        self.assertAlmostEqual(float(result["vb_v"]), 1.954004, places=5)
        self.assertAlmostEqual(float(result["vc_v"]), 9.438841, places=5)
        self.assertAlmostEqual(float(result["ic_ma"]), (12.0 - 9.438841) / 2.2, places=5)

    def test_ac_gain_and_phase_are_computed_from_run(self) -> None:
        result = run_simulation(
            {**BASE, "analysis": "ac"},
            executable="ngspice",
            runner=runner_for(AC_LOG),
        )
        series = result["series"]
        self.assertEqual(len(series), 3)
        self.assertAlmostEqual(series[0]["gain_db"], 13.9794, places=3)
        self.assertAlmostEqual(series[0]["phase_deg"], -170.0, places=3)

    def test_ac_parser_merges_paginated_column_groups(self) -> None:
        result = run_simulation(
            {**BASE, "analysis": "ac"},
            executable="ngspice",
            runner=runner_for(AC_SPLIT_LOG),
        )
        self.assertEqual(len(result["series"]), 2)
        self.assertAlmostEqual(result["series"][1]["gain_db"], 26.0206, places=3)
        self.assertAlmostEqual(result["series"][1]["phase_deg"], -179.0, places=3)

    def test_transient_inverts_phase(self) -> None:
        result = run_simulation(
            {**BASE, "analysis": "transient"},
            executable="ngspice",
            runner=runner_for(TRAN_LOG),
        )
        self.assertIn("กลับเฟส", result["phase_note"])
        self.assertGreater(float(result["vin_peak_mv"]), 0.0)

    def test_charts_are_svg_with_units(self) -> None:
        ac = run_simulation(
            {**BASE, "analysis": "ac"},
            executable="ngspice",
            runner=runner_for(AC_LOG),
        )
        tran = run_simulation(
            {**BASE, "analysis": "transient"},
            executable="ngspice",
            runner=runner_for(TRAN_LOG),
        )
        self.assertIn("Bode", bode_svg(ac["series"]))
        self.assertIn("mV", waveform_svg(tran["series"]))


class ErrorPathTests(unittest.TestCase):
    def test_missing_engine_is_error(self) -> None:
        with patch.object(spice_engine.shutil, "which", return_value=None):
            with self.assertRaises(EngineUnavailable):
                run_simulation(BASE)

    def test_nonzero_returncode_is_error(self) -> None:
        with self.assertRaises(SimulationError):
            run_simulation(
                BASE, executable="ngspice", runner=runner_for("fatal error", 1)
            )

    def test_empty_op_log_is_error(self) -> None:
        with self.assertRaises(SimulationError):
            run_simulation(BASE, executable="ngspice", runner=runner_for("no data"))

    def test_timeout_is_error(self) -> None:
        def timeout_run(cmd: list[str], cwd: Path, timeout: int):
            raise subprocess.TimeoutExpired(cmd, timeout)

        with self.assertRaises(SimulationError):
            run_simulation(BASE, executable="ngspice", runner=timeout_run)


if __name__ == "__main__":
    unittest.main()
