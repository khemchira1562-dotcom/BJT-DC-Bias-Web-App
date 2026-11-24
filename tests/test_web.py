"""HTTP-level tests using Flask's test client."""

import unittest
from unittest.mock import patch

import app as app_module
from app import app
from spice_engine import EngineUnavailable

REFERENCE = {
    "mode": "divider",
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "beta": "100",
    "vbe": "0.7",
}


class WebTests(unittest.TestCase):
    def setUp(self) -> None:
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_get_index_returns_form(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        for field in ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"):
            self.assertIn(f'name="{field}"', body)
        self.assertIn("Calculate DC Bias", body)
        # Nothing is calculated on GET.
        self.assertNotIn("9.294", body)

    def test_post_valid_inputs_returns_results(self) -> None:
        response = self.client.post("/", data=REFERENCE)
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("9.294", body)   # VC
        self.assertIn("8.052", body)   # VCE
        self.assertIn("1.942", body)   # VB
        self.assertIn("mA", body)
        self.assertIn("µA", body)
        self.assertIn("Active", body)

    def test_results_come_from_backend_not_template(self) -> None:
        response = self.client.post("/", data={**REFERENCE, "rc": "4.4"})
        body = response.get_data(as_text=True)
        self.assertIn("6.589", body)  # VC = 12 - 1.2298mA * 4.4k
        self.assertNotIn("9.294", body)

    def test_invalid_input_returns_400_with_message(self) -> None:
        response = self.client.post("/", data={**REFERENCE, "r1": "0"})
        self.assertEqual(response.status_code, 400)
        body = response.get_data(as_text=True)
        self.assertIn("มากกว่า 0", body)

    def test_non_numeric_input_returns_400(self) -> None:
        response = self.client.post("/", data={**REFERENCE, "vbe": "abc"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("ต้องเป็นตัวเลข", response.get_data(as_text=True))

    def test_missing_field_returns_400(self) -> None:
        data = dict(REFERENCE)
        del data["beta"]
        response = self.client.post("/", data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("กรุณากรอก", response.get_data(as_text=True))

    def test_cutoff_shows_warning(self) -> None:
        response = self.client.post("/", data={**REFERENCE, "r2": "1"})
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Cutoff", body)
        self.assertIn("Forward-Active", body)

    def test_saturation_shows_warning(self) -> None:
        response = self.client.post("/", data={**REFERENCE, "rc": "10"})
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Saturation", body)


class Lab04WebTests(unittest.TestCase):
    """The web route delegates to the adapter and never fakes a result."""

    def setUp(self) -> None:
        app.config.update(TESTING=True)
        self.client = app.test_client()
        self.data = {
            **REFERENCE,
            "action": "simulate",
            "analysis": "dc",
            "rl": "10",
            "cin_uf": "10",
            "cout_uf": "10",
            "amplitude_mv": "10",
            "frequency_khz": "1",
            "model": ".model TEST_NPN NPN",
            "fmin_hz": "10",
            "fmax_hz": "1000000",
            "tran_stop_ms": "5",
        }

    def test_get_index_shows_lab04_controls(self) -> None:
        body = self.client.get("/").get_data(as_text=True)
        for field in ("analysis", "rl", "cin_uf", "cout_uf", "amplitude_mv",
                      "frequency_khz", "model", "fmin_hz", "fmax_hz",
                      "tran_stop_ms"):
            self.assertIn(f'name="{field}"', body)
        self.assertIn("Run Simulation", body)
        self.assertIn("mV peak", body)
        self.assertIn("µF", body)
        self.assertNotIn("Simulation Results", body)

    @staticmethod
    def dc_result() -> dict[str, object]:
        return {
            "analysis": "dc",
            "engine": "ngspice",
            "engine_status": "success",
            "model": ".model TEST_NPN NPN",
            "model_name": "TEST_NPN",
            "netlist": "VCC vcc 0 DC 12\n.op\n.end\n",
            "log_tail": "--- Operating Point ---\nV(collector)=9.500000\n",
            "warnings": [],
            "vb_v": 1.94,
            "ve_v": 1.24,
            "vc_v": 9.50,
            "vce_v": 8.26,
            "ic_ma": 1.136,
            "ie_ma": 1.24,
        }

    def test_simulate_dc_shows_provenance_and_units(self) -> None:
        with patch.object(app_module, "run_simulation", return_value=self.dc_result()):
            response = self.client.post("/", data=self.data)
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Simulation Results", body)
        self.assertIn("ngspice · success", body)
        self.assertIn("9.500 V", body)
        self.assertIn("1.136 mA", body)
        self.assertIn("Netlist ที่ส่งให้ ngspice", body)
        self.assertIn("Engine log", body)

    def test_engine_unavailable_has_no_stale_results(self) -> None:
        message = "ไม่พบ ngspice ใน PATH"
        with patch.object(app_module, "run_simulation", side_effect=EngineUnavailable(message)):
            response = self.client.post("/", data=self.data)
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 400)
        self.assertIn(message, body)
        self.assertNotIn("Simulation Results", body)
        self.assertNotIn("DC Bias Results", body)

    def test_ac_result_renders_svg_from_parsed_series(self) -> None:
        result = {
            "analysis": "ac",
            "engine": "ngspice",
            "engine_status": "success",
            "model": ".model TEST_NPN NPN",
            "model_name": "TEST_NPN",
            "netlist": ".ac dec 20 10 1e6\n.end\n",
            "log_tail": "Index frequency vm(vin) vm(vout)\n",
            "warnings": [],
            "series": [
                {"frequency_hz": 10.0, "gain_db": 20.0, "phase_deg": -170.0},
                {"frequency_hz": 1000.0, "gain_db": 26.0, "phase_deg": -179.0},
            ],
            "summary": {
                "fmin_hz": 10.0,
                "fmax_hz": 1000.0,
                "peak_gain_db": 26.0,
                "peak_gain_freq_hz": 1000.0,
                "peak_phase_deg": -179.0,
                "f3db_hz": 100.0,
            },
        }
        with patch.object(app_module, "run_simulation", return_value=result):
            body = self.client.post("/", data={**self.data, "analysis": "ac"}).get_data(as_text=True)
        self.assertIn("<svg", body)
        self.assertIn("Bode", body)
        self.assertIn("Frequency (Hz)", body)
        self.assertIn("26.00 dB", body)

    def test_transient_result_renders_waveform_with_units(self) -> None:
        result = {
            "analysis": "transient",
            "engine": "ngspice",
            "engine_status": "success",
            "model": ".model TEST_NPN NPN",
            "model_name": "TEST_NPN",
            "netlist": ".tran 1e-5 5e-3\n.end\n",
            "log_tail": "Index time v(vin) v(vout)\n",
            "warnings": [],
            "series": [
                {"time_s": 0.0, "vin_v": 0.0, "vout_v": 0.0},
                {"time_s": 1e-5, "vin_v": 0.01, "vout_v": -0.05},
            ],
            "vin_peak_mv": 10.0,
            "vout_peak_mv": 50.0,
            "phase_note": "Vout กลับเฟสกับ Vin",
        }
        with patch.object(app_module, "run_simulation", return_value=result):
            body = self.client.post("/", data={**self.data, "analysis": "transient"}).get_data(as_text=True)
        self.assertIn("Transient response", body)
        self.assertIn("mV", body)
        self.assertIn("Vin", body)
        self.assertIn("Vout", body)
        self.assertIn("50.00 mV", body)

    def test_layout_action_does_not_run_simulation(self) -> None:
        with patch.object(app_module, "run_simulation") as simulate:
            response = self.client.post("/", data={**self.data, "action": "layout"})
        self.assertEqual(response.status_code, 200)
        simulate.assert_not_called()
        self.assertNotIn("Simulation Results", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
