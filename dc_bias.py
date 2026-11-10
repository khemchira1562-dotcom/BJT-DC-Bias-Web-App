"""BJT DC bias calculations: NPN common-emitter, voltage-divider bias.

Engineering logic only. This module must not import Flask or know anything
about HTML/HTTP. Resistances are entered in kilo-ohms (kΩ) and converted to
ohms internally.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

# Collector-emitter voltage below which the transistor is flagged as
# saturated by this simple Forward-Active model.
VCE_SAT = 0.3  # V

FIELD_NAMES = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")

FIELD_LABELS = {
    "vcc": "VCC (V)",
    "r1": "R1 (kΩ)",
    "r2": "R2 (kΩ)",
    "rc": "RC (kΩ)",
    "re": "RE (kΩ)",
    "beta": "β (Beta)",
    "vbe": "VBE (V)",
}


class InputError(ValueError):
    """Raised when user input is missing, non-numeric, or physically invalid."""


@dataclass(frozen=True)
class BiasInputs:
    """Circuit inputs. Resistances are in kΩ, voltages in V."""

    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float


@dataclass(frozen=True)
class BiasResult:
    """DC operating point. Currents in A, voltages in V, RTH in kΩ."""

    vth: float
    rth: float
    ib: float
    ic: float
    ie: float
    vb: float
    ve: float
    vc: float
    vce: float
    region: str
    warnings: tuple[str, ...] = ()


def _to_float(raw: object, label: str) -> float:
    text = str(raw).strip()
    if not text:
        raise InputError(f"กรุณากรอก {label}")
    if "," in text:
        text = text.replace(",", "")
    try:
        value = float(text)
    except ValueError:
        raise InputError(f"{label} ต้องเป็นตัวเลข") from None
    if not math.isfinite(value):
        raise InputError(f"{label} ต้องเป็นค่าจำกัด (ไม่ใช่ inf หรือ nan)")
    return value


def parse_inputs(raw: Mapping[str, object]) -> BiasInputs:
    """Convert raw form values to validated :class:`BiasInputs`.

    Raises :class:`InputError` with a readable Thai message on the first
    problem found.
    """
    values = {name: _to_float(raw.get(name, ""), FIELD_LABELS[name]) for name in FIELD_NAMES}

    for name in ("vcc", "r1", "r2", "rc", "re"):
        if values[name] <= 0:
            raise InputError(f"{FIELD_LABELS[name]} ต้องมากกว่า 0")

    if values["beta"] <= 0:
        raise InputError("β (Beta) ต้องมากกว่า 0")
    if values["vbe"] < 0:
        raise InputError("VBE (V) ต้องไม่ติดลบ")
    if values["vbe"] >= values["vcc"]:
        raise InputError("VBE (V) ต้องน้อยกว่า VCC (V)")

    return BiasInputs(
        vcc=values["vcc"],
        r1=values["r1"],
        r2=values["r2"],
        rc=values["rc"],
        re=values["re"],
        beta=values["beta"],
        vbe=values["vbe"],
    )


def calculate(inputs: BiasInputs) -> BiasResult:
    """Solve the DC operating point using the Forward-Active approximation."""
    r1, r2 = inputs.r1, inputs.r2
    vth = inputs.vcc * r2 / (r1 + r2)
    rth = r1 * r2 / (r1 + r2)  # kΩ

    if vth <= inputs.vbe:
        return BiasResult(
            vth=vth,
            rth=rth,
            ib=0.0,
            ic=0.0,
            ie=0.0,
            vb=vth,
            ve=0.0,
            vc=inputs.vcc,
            vce=inputs.vcc,
            region="cutoff",
            warnings=(
                "VTH ≤ VBE: ทรานซิสเตอร์อยู่ในช่วง Cutoff "
                "สมการ Forward-Active ใช้ไม่ได้ ค่าที่แสดงคือกรณีกระแสเป็นศูนย์",
            ),
        )

    ib = (vth - inputs.vbe) / ((rth + (inputs.beta + 1.0) * inputs.re) * 1000.0)
    ic = inputs.beta * ib
    ie = (inputs.beta + 1.0) * ib

    ve = ie * inputs.re * 1000.0
    vb = ve + inputs.vbe
    vc = inputs.vcc - ic * inputs.rc * 1000.0
    vce = vc - ve

    warnings: tuple[str, ...] = ()
    region = "active"
    if vce < VCE_SAT:
        region = "saturation"
        warnings = (
            f"VCE = {vce:.3f} V ต่ำกว่า VCE_SAT = {VCE_SAT:.1f} V: "
            "ทรานซิสเตอร์อาจอยู่ในช่วง Saturation "
            "ค่า DC Bias จาก Forward-Active Approximation ไม่น่าเชื่อถือ",
        )

    return BiasResult(
        vth=vth,
        rth=rth,
        ib=ib,
        ic=ic,
        ie=ie,
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vce,
        region=region,
        warnings=warnings,
    )
