"""ngspice adapter for the Lab 04 CE amplifier simulator.

Engineering logic only: no Flask, no HTML. The adapter validates inputs,
builds one netlist for the reference voltage-divider CE circuit, calls the
external ngspice process, and parses the numbers out of its real output.
No simulation result is stored here as a constant.
"""

from __future__ import annotations

import math
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

ENGINE = "ngspice"
MODES: tuple[str, ...] = ("dc", "ac", "transient")
MODE_LABELS = {
    "dc": "DC operating point (.op)",
    "ac": "AC frequency response (.ac)",
    "transient": "Transient waveform (.tran)",
}

FIELD_NAMES = (
    "vcc",
    "r1",
    "r2",
    "rc",
    "re",
    "rl",
    "cin_uf",
    "cout_uf",
    "amplitude_mv",
    "frequency_khz",
    "model",
    "fmin_hz",
    "fmax_hz",
    "tran_stop_ms",
)

# ngspice's built-in default NPN model. This is a structural default ONLY:
# it is not an instructor-verified Starter Kit model and must be labelled as
# such in the UI and in validation notes.
DEFAULT_MODEL = ".model QNPN_LAB04 NPN"

MODEL_RE = re.compile(
    r"^\.model[ \t]+([A-Za-z0-9_]+)[ \t]+npn(?:[ \t]+[A-Za-z0-9_.=+\-]+)*$",
    re.IGNORECASE,
)
NUMBER_RE = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")
NODE_V_RE = re.compile(
    r"V\(\s*([A-Za-z0-9_#]+)\s*\)\s*[:=]?\s*([-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?)",
    re.IGNORECASE,
)
FAILURE_RE = re.compile(
    r"fatal error|convergence failed|no convergence|error in|unrecognized|"
    r"unknown parameter|could not find|syntax error",
    re.IGNORECASE,
)

Runner = Callable[[list[str], Path, int], tuple[int, str, str]]


class SpiceError(ValueError):
    """Base class for adapter errors with a readable Thai message."""


class InputError(SpiceError):
    """Invalid engineering input: never handed to the solver."""


class EngineUnavailable(SpiceError):
    """ngspice executable missing or impossible to start."""


class SimulationError(SpiceError):
    """ngspice failed, timed out, or produced unusable output."""


@dataclass(frozen=True)
class SpiceInputs:
    """Validated inputs. Resistances are in kΩ, capacitances in µF."""

    analysis: str
    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    rl: float
    cin_uf: float
    cout_uf: float
    amplitude_mv: float
    frequency_khz: float
    model: str
    model_name: str
    fmin_hz: float
    fmax_hz: float
    tran_stop_ms: float


def _to_float(raw: object, label: str) -> float:
    text = str(raw).strip().replace(",", "")
    if not text:
        raise InputError(f"กรุณากรอก {label}")
    try:
        value = float(text)
    except ValueError:
        raise InputError(f"{label} ต้องเป็นตัวเลข") from None
    if not math.isfinite(value):
        raise InputError(f"{label} ต้องเป็นค่าจำกัด (ไม่ใช่ inf หรือ nan)")
    return value


def parse_spice_inputs(raw: Mapping[str, object]) -> SpiceInputs:
    """Validate every value before it is allowed near the netlist."""
    analysis = str(raw.get("analysis", "")).strip().lower()
    if not analysis:
        raise InputError("กรุณาเลือกโหมดการจำลอง (dc, ac, transient)")
    if analysis not in MODES:
        raise InputError(
            f"โหมดการจำลองไม่รู้จัก: {analysis} (รองรับ: dc, ac, transient)"
        )

    labels = {
        "vcc": "VCC (V)",
        "r1": "R1 (kΩ)",
        "r2": "R2 (kΩ)",
        "rc": "RC (kΩ)",
        "re": "RE (kΩ)",
        "rl": "RL (kΩ)",
        "cin_uf": "Cin (µF)",
        "cout_uf": "Cout (µF)",
        "amplitude_mv": "Amplitude (mV peak)",
        "frequency_khz": "Frequency (kHz)",
        "fmin_hz": "AC fmin (Hz)",
        "fmax_hz": "AC fmax (Hz)",
        "tran_stop_ms": "Transient stop (ms)",
    }
    values = {name: _to_float(raw.get(name, ""), labels[name]) for name in labels}

    for name in ("vcc", "r1", "r2", "rc", "re", "rl", "cin_uf", "cout_uf"):
        if values[name] <= 0:
            raise InputError(f"{labels[name]} ต้องมากกว่า 0")
    if values["amplitude_mv"] < 0:
        raise InputError("Amplitude (mV peak) ต้องไม่ติดลบ")
    if values["frequency_khz"] <= 0:
        raise InputError("Frequency (kHz) ต้องมากกว่า 0")
    if values["tran_stop_ms"] <= 0:
        raise InputError("Transient stop (ms) ต้องมากกว่า 0")
    if values["fmin_hz"] <= 0 or values["fmax_hz"] <= values["fmin_hz"]:
        raise InputError("AC fmax (Hz) ต้องมากกว่า AC fmin (Hz)")
    if values["fmax_hz"] > 1e9:
        raise InputError("AC fmax (Hz) ต้องไม่เกิน 1 GHz")

    model = str(raw.get("model", "")).strip()
    if any(char in model for char in ("\n", "\r", ";", "$")):
        raise InputError(
            "BJT model ต้องเป็นบรรทัด .model <ชื่อ> NPN ... เท่านั้น "
            "(ห้ามมีบรรทัดใหม่หรือคำสั่งอื่น)"
        )
    match = MODEL_RE.fullmatch(model)
    if not match:
        raise InputError(
            "BJT model ต้องเป็นบรรทัด .model <ชื่อ> NPN ... เท่านั้น "
            "(ห้ามมีบรรทัดใหม่หรือคำสั่งอื่น)"
        )

    return SpiceInputs(
        analysis=analysis,
        vcc=values["vcc"],
        r1=values["r1"],
        r2=values["r2"],
        rc=values["rc"],
        re=values["re"],
        rl=values["rl"],
        cin_uf=values["cin_uf"],
        cout_uf=values["cout_uf"],
        amplitude_mv=values["amplitude_mv"],
        frequency_khz=values["frequency_khz"],
        model=model,
        model_name=match.group(1),
        fmin_hz=values["fmin_hz"],
        fmax_hz=values["fmax_hz"],
        tran_stop_ms=values["tran_stop_ms"],
    )


def build_netlist(i: SpiceInputs) -> str:
    """Return one analysis-only netlist. Never mix .control with batch mode."""
    amplitude_v = i.amplitude_mv / 1000.0
    frequency_hz = i.frequency_khz * 1000.0
    lines = [
        "* Lab 04 CE voltage-divider reference — generated by spice_engine.py",
        f"VCC vcc 0 DC {i.vcc:g}",
        f"R1 vcc base {i.r1:g}k",
        f"R2 base 0 {i.r2:g}k",
        f"RC vcc collector {i.rc:g}k",
        f"RE emitter 0 {i.re:g}k",
        f"Q1 collector base emitter {i.model_name}",
        f"CIN vin base {i.cin_uf:g}u",
        f"COUT collector vout {i.cout_uf:g}u",
        f"RL vout 0 {i.rl:g}k",
        (
            f"VIN vin 0 DC 0 AC {amplitude_v:.6g} "
            f"SIN(0 {amplitude_v:.6g} {frequency_hz:.6g})"
        ),
        i.model,
    ]

    if i.analysis == "dc":
        lines.append(".op")
    elif i.analysis == "ac":
        lines.append(f".ac dec 20 {i.fmin_hz:g} {i.fmax_hz:g}")
        lines.append(".print ac vm(vin) vm(vout) vp(vin) vp(vout)")
    else:
        stop_s = i.tran_stop_ms / 1000.0
        step_s = stop_s / 500.0
        lines.append(f".tran {step_s:.9g} {stop_s:.9g}")
        lines.append(".print tran v(vin) v(vout)")

    lines.append(".end")
    return "\n".join(lines) + "\n"


def _default_runner(cmd: list[str], cwd: Path, timeout: int) -> tuple[int, str, str]:
    """Run ngspice in batch mode and return (returncode, log text, stderr)."""
    completed = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    log_path = cwd / "run.log"
    log_text = (
        log_path.read_text(encoding="utf-8", errors="replace")
        if log_path.exists()
        else completed.stdout
    )
    return completed.returncode, log_text, completed.stderr


def _log_tail(text: str, limit: int = 1800) -> str:
    return text[-limit:] if len(text) > limit else text


def _check_log(returncode: int, log_text: str, stderr: str) -> None:
    if returncode != 0 or FAILURE_RE.search(log_text):
        detail = _log_tail(log_text) or _log_tail(stderr)
        raise SimulationError(
            "ngspice รันไม่สำเร็จ (ผลที่แสดงต้องไม่ถูกนำไปใช้): "
            + (detail or "ไม่มีข้อความจาก engine")
        )


def _parse_operating_point(log_text: str, i: SpiceInputs) -> dict[str, object]:
    nodes = {name.lower(): float(value) for name, value in NODE_V_RE.findall(log_text)}
    required = ("vcc", "base", "collector", "emitter")
    missing = [name for name in required if name not in nodes]
    if missing:
        raise SimulationError(
            "ไม่พบ node " + ", ".join(missing) + " ใน ngspice .op output — "
            "ห้ามใช้ค่าที่เดาจาก netlist แทน"
        )

    vcc = nodes["vcc"]
    vb = nodes["base"]
    vc = nodes["collector"]
    ve = nodes["emitter"]
    vce = vc - ve
    ic_ma = (vcc - vc) / i.rc  # kΩ → mA
    ie_ma = ve / i.re

    warnings: list[str] = []
    if vce <= 0.2:
        warnings.append(
            f"VCE = {vce:.3f} V ≤ 0.2 V: ngspice อยู่ในช่วง Saturation "
            "แบบจำลอง Forward-Active ของ Lab 3 ใช้เปรียบเทียบไม่ได้"
        )
    return {
        "vb_v": vb,
        "ve_v": ve,
        "vc_v": vc,
        "vce_v": vce,
        "ic_ma": ic_ma,
        "ie_ma": ie_ma,
        "warnings": warnings,
    }


def _parse_print_table(log_text: str, columns: tuple[str, ...]) -> list[dict[str, float]]:
    """Parse a ngspice batch .print table into rows keyed by column name."""
    lines = log_text.splitlines()
    for index, line in enumerate(lines):
        lowered = line.lower()
        if not all(column.lower() in lowered for column in columns):
            continue

        header = [token.lower() for token in re.findall(r"[A-Za-z0-9_#()\.\-]+", line)]
        if header and header[0] == "index":
            header = header[1:]
        has_scale = any(token in ("frequency", "time") for token in header)
        if not has_scale:
            header = ["scale", *header]

        rows: list[dict[str, float]] = []
        for row in lines[index + 1 :]:
            numbers = NUMBER_RE.findall(row)
            if not numbers:
                if rows:
                    break
                continue
            if len(numbers) == len(header) + 1 and re.fullmatch(
                r"\d+", numbers[0]
            ):
                numbers = numbers[1:]
            if len(numbers) != len(header):
                if rows:
                    break
                continue
            rows.append(
                {name: float(value) for name, value in zip(header, numbers)}
            )
        if rows:
            return rows
    raise SimulationError("ไม่พบตารางผลลัพธ์จากคำสั่ง .print ของ ngspice")


def _normalise_phase(degrees: float) -> float:
    return (degrees + 180.0) % 360.0 - 180.0


def _parse_ac(log_text: str) -> dict[str, object]:
    rows = _parse_print_table(
        log_text, ("vm(vin)", "vm(vout)", "vp(vin)", "vp(vout)")
    )
    series: list[dict[str, float]] = []
    for row in rows:
        scale = row.get("frequency", row.get("scale"))
        if scale is None:
            continue
        vin = row["vm(vin)"]
        vout = row["vm(vout)"]
        magnitude = vout / vin if vin > 0 else 0.0
        series.append(
            {
                "frequency_hz": float(scale),
                "gain_db": 20.0 * math.log10(magnitude) if magnitude > 0 else -120.0,
                "phase_deg": _normalise_phase(row["vp(vout)"] - row["vp(vin)"]),
            }
        )
    if not series:
        raise SimulationError("ตาราง .ac ของ ngspice ไม่มีข้อมูลความถี่ที่อ่านได้")

    peak = max(series, key=lambda row: row["gain_db"])
    summary: dict[str, object] = {
        "fmin_hz": series[0]["frequency_hz"],
        "fmax_hz": series[-1]["frequency_hz"],
        "peak_gain_db": peak["gain_db"],
        "peak_gain_freq_hz": peak["frequency_hz"],
        "peak_phase_deg": peak["phase_deg"],
    }
    warnings: list[str] = []
    cutoff = next(
        (row for row in series if row["gain_db"] <= peak["gain_db"] - 3.0), None
    )
    if cutoff is None:
        warnings.append(
            "ไม่พบจุดตัด −3 dB ในช่วง sweep นี้ (not determined in sweep range) "
            "— ห้ามสร้างตัวเลข fL/fH ขึ้นเอง"
        )
    else:
        summary["f3db_hz"] = cutoff["frequency_hz"]

    return {"series": series, "summary": summary, "warnings": warnings}


def _parse_transient(log_text: str) -> dict[str, object]:
    rows = _parse_print_table(log_text, ("v(vin)", "v(vout)"))
    series: list[dict[str, float]] = []
    for row in rows:
        scale = row.get("time", row.get("scale"))
        if scale is None:
            continue
        series.append(
            {
                "time_s": float(scale),
                "vin_v": row["v(vin)"],
                "vout_v": row["v(vout)"],
            }
        )
    if len(series) < 2:
        raise SimulationError("ตาราง .tran ของ ngspice มีข้อมูลไม่เพียงพอ")

    start = int(len(series) * 0.6)
    tail = series[start:] or series
    xs = [point["vin_v"] for point in tail]
    ys = [point["vout_v"] for point in tail]
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    covariance = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    variance = math.sqrt(
        sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)
    )
    correlation = covariance / variance if variance > 0 else 0.0
    if correlation <= -0.5:
        phase_note = "Vout กลับเฟสกับ Vin (สอดคล้องกับ Common-Emitter)"
    elif correlation >= 0.5:
        phase_note = "Vout ไม่กลับเฟสกับ Vin — ตรวจจุดวัดอีกครั้ง"
    else:
        phase_note = "ไม่สรุปทิศทางเฟสจากช่วงข้อมูลนี้ (correlation ใกล้ศูนย์)"

    return {
        "series": series,
        "vin_peak_mv": max(abs(value) for value in xs) * 1000.0,
        "vout_peak_mv": max(abs(value) for value in ys) * 1000.0,
        "phase_note": phase_note,
        "warnings": [],
    }


def run_simulation(
    raw: Mapping[str, object],
    *,
    runner: Runner | None = None,
    executable: str | None = None,
    timeout: int = 30,
) -> dict[str, object]:
    """Validate → netlist → real ngspice run → parse. Returns units + provenance."""
    inputs = parse_spice_inputs(raw)
    exe = executable or shutil.which(ENGINE)
    if not exe:
        raise EngineUnavailable(
            "ไม่พบ ngspice ใน PATH ของเครื่องที่รัน Flask "
            "จึงยังรันจำลองไม่ได้ (ห้ามแสดงผลสำเร็จหรือกราฟเก่า)"
        )

    netlist = build_netlist(inputs)
    run = runner or _default_runner
    with tempfile.TemporaryDirectory(prefix="lab04-ngspice-") as directory:
        cwd = Path(directory)
        (cwd / "circuit.cir").write_text(netlist, encoding="utf-8")
        try:
            returncode, log_text, stderr = run(
                [exe, "-b", "-o", "run.log", "circuit.cir"], cwd, timeout
            )
        except subprocess.TimeoutExpired as exc:
            raise SimulationError(
                f"ngspice หมดเวลา ({timeout} วิ) — ไม่มีผลจำลองที่เชื่อถือได้"
            ) from exc
        except OSError as exc:
            raise EngineUnavailable(f"เรียก ngspice ไม่ได้: {exc}") from exc

    _check_log(returncode, log_text, stderr)

    if inputs.analysis == "dc":
        payload = _parse_operating_point(log_text, inputs)
    elif inputs.analysis == "ac":
        payload = _parse_ac(log_text)
    else:
        payload = _parse_transient(log_text)

    return {
        "analysis": inputs.analysis,
        "engine": ENGINE,
        "engine_status": "success",
        "model": inputs.model,
        "model_name": inputs.model_name,
        "netlist": netlist,
        "log_tail": _log_tail(log_text),
        "warnings": payload["warnings"],
        **{key: value for key, value in payload.items() if key != "warnings"},
    }
