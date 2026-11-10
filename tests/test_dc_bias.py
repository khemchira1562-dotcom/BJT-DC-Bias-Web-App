"""Unit tests for the engineering calculations in dc_bias.py."""

import unittest

from dc_bias import (
    VCE_SAT,
    BiasInputs,
    InputError,
    calculate,
    parse_inputs,
)

REFERENCE = {
    "vcc": 12.0,
    "r1": 100.0,
    "r2": 22.0,
    "rc": 2.2,
    "re": 1.0,
    "beta": 100.0,
    "vbe": 0.7,
}


def solve(**overrides: float):
    values = {**REFERENCE, **overrides}
    return calculate(parse_inputs(values))


class ReferencePointTests(unittest.TestCase):
    """Values from the Lab 02 handout: VCC=12V, R1=100k, R2=22k,
    RC=2.2k, RE=1k, beta=100, VBE=0.70V."""

    def setUp(self) -> None:
        self.result = solve()

    def test_thevenin_voltage(self) -> None:
        self.assertAlmostEqual(self.result.vth, 2.1639, places=4)

    def test_thevenin_resistance_in_kohm(self) -> None:
        self.assertAlmostEqual(self.result.rth, 18.0328, places=4)

    def test_base_current(self) -> None:
        self.assertAlmostEqual(self.result.ib, 1.2298e-5, delta=1e-9)

    def test_collector_current(self) -> None:
        self.assertAlmostEqual(self.result.ic, 1.2298e-3, delta=1e-7)

    def test_emitter_current(self) -> None:
        self.assertAlmostEqual(self.result.ie, 1.2421e-3, delta=1e-7)

    def test_voltages(self) -> None:
        self.assertAlmostEqual(self.result.ve, 1.2422, delta=0.001)
        self.assertAlmostEqual(self.result.vb, 1.9422, delta=0.001)
        self.assertAlmostEqual(self.result.vc, 9.2943, delta=0.001)
        self.assertAlmostEqual(self.result.vce, 8.0522, delta=0.001)

    def test_region_is_active(self) -> None:
        self.assertEqual(self.result.region, "active")
        self.assertEqual(self.result.warnings, ())

    def test_kohm_inputs_are_converted(self) -> None:
        # 100 kΩ must behave like 100000 Ω, not 100 Ω.
        inputs = parse_inputs(REFERENCE)
        self.assertEqual(inputs.r1, 100.0)
        self.assertGreater(self.result.rth, 1.0)  # 18 kΩ, not 0.018


class RegionTests(unittest.TestCase):
    def test_cutoff_when_vth_below_vbe(self) -> None:
        result = solve(r2=1.0)  # VTH ~= 0.119 V < 0.7 V
        self.assertEqual(result.region, "cutoff")
        self.assertEqual(result.ic, 0.0)
        self.assertEqual(result.ie, 0.0)
        self.assertEqual(result.vce, REFERENCE["vcc"])
        self.assertTrue(result.warnings)

    def test_saturation_when_vce_below_threshold(self) -> None:
        result = solve(rc=10.0)  # VC = 12 - 1.23mA*10k -> negative VCE
        self.assertEqual(result.region, "saturation")
        self.assertLess(result.vce, VCE_SAT)
        self.assertTrue(result.warnings)


class ValidationTests(unittest.TestCase):
    def assert_invalid(self, **overrides: object) -> None:
        values = {**REFERENCE, **overrides}
        with self.assertRaises(InputError):
            parse_inputs(values)

    def test_zero_resistance_is_rejected(self) -> None:
        self.assert_invalid(r1=0)

    def test_negative_resistance_is_rejected(self) -> None:
        self.assert_invalid(re=(-1))

    def test_non_positive_beta_is_rejected(self) -> None:
        self.assert_invalid(beta=0)
        self.assert_invalid(beta=(-50))

    def test_non_positive_vcc_is_rejected(self) -> None:
        self.assert_invalid(vcc=0)

    def test_non_numeric_value_is_rejected(self) -> None:
        self.assert_invalid(vbe="abc")

    def test_missing_value_is_rejected(self) -> None:
        values = {k: str(v) for k, v in REFERENCE.items()}
        del values["rc"]
        with self.assertRaises(InputError):
            parse_inputs(values)

    def test_vbe_must_be_below_vcc(self) -> None:
        self.assert_invalid(vbe=12.0)

    def test_infinite_value_is_rejected(self) -> None:
        self.assert_invalid(r1="inf")

    def test_error_message_is_readable(self) -> None:
        with self.assertRaises(InputError) as ctx:
            parse_inputs({**REFERENCE, "r1": "0"})
        self.assertIn("มากกว่า 0", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
