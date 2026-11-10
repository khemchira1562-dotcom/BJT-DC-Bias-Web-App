"""HTTP-level tests using Flask's test client."""

import unittest

from app import app

REFERENCE = {
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


if __name__ == "__main__":
    unittest.main()
