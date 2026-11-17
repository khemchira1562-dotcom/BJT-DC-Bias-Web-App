"""BJT DC bias calculations: NPN common-emitter, three bias modes.

Engineering logic only. This module must not import Flask or know anything
about HTML/HTTP. Resistances are entered in kilo-ohms (kΩ) and converted to
ohms internally.

Modes:
    divider  Voltage-divider bias (R1, R2, RE)
    fixed    Fixed bias (RB only, emitter grounded)
    emitter  Emitter bias (RB, RE)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Mapping

# Collector-emitter voltage at or below which the transistor is flagged as
# saturated by this simple Forward-Active model. Lab 03 fixes this at 0.2 V.
VCE_SAT = 0.2  # V

MODE_DIVIDER = "divider"
MODE_FIXED = "fixed"
MODE_EMITTER = "emitter"
MODES: tuple[str, ...] = (MODE_DIVIDER, MODE_FIXED, MODE_EMITTER)

MODE_LABELS = {
    MODE_DIVIDER: "Voltage Divider Bias",
    MODE_FIXED: "Fixed Bias",
    MODE_EMITTER: "Emitter Bias",
}

FIELD_NAMES = ("vcc", "r1", "r2", "rb", "rc", "re", "beta", "vbe")

FIELD_LABELS = {
    "vcc": "VCC (V)",
    "r1": "R1 (kΩ)",
    "r2": "R2 (kΩ)",
    "rb": "RB (kΩ)",
    "rc": "RC (kΩ)",
    "re": "RE (kΩ)",
    "beta": "β (Beta)",
    "vbe": "VBE (V)",
}

# Which fields each mode actually reads. Everything else is ignored, so a
# value left over from another mode can never poison the result.
MODE_FIELDS: dict[str, tuple[str, ...]] = {
    MODE_DIVIDER: ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"),
    MODE_FIXED: ("vcc", "rb", "rc", "beta", "vbe"),
    MODE_EMITTER: ("vcc", "rb", "rc", "re", "beta", "vbe"),
}

# Fields that must be strictly positive (resistances in kΩ, plus VCC).
POSITIVE_FIELDS = ("vcc", "r1", "r2", "rb", "rc", "re")


class InputError(ValueError):
    """Raised when user input is missing, non-numeric, or physically invalid."""


@dataclass(frozen=True)
class BiasInputs:
    """Circuit inputs. Resistances are in kΩ, voltages in V.

    Fields a mode does not use are ``None``.
    """

    mode: str
    vcc: float
    rc: float
    beta: float
    vbe: float
    r1: float | None = None
    r2: float | None = None
    rb: float | None = None
    re: float | None = None


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
    problem found. Only the fields the selected mode needs are read.
    """
    mode = str(raw.get("mode", "")).strip()
    if not mode:
        raise InputError("กรุณาเลือกโหมดไบอัส (divider, fixed, emitter)")
    if mode not in MODES:
        raise InputError(
            f"โหมดไบอัสไม่รู้จัก: {mode} (รองรับ: divider, fixed, emitter)"
        )

    names = MODE_FIELDS[mode]
    values = {name: _to_float(raw.get(name, ""), FIELD_LABELS[name]) for name in names}

    for name in names:
        if name in POSITIVE_FIELDS and values[name] <= 0:
            raise InputError(f"{FIELD_LABELS[name]} ต้องมากกว่า 0")

    if values["beta"] <= 0:
        raise InputError("β (Beta) ต้องมากกว่า 0")
    if values["vbe"] < 0:
        raise InputError("VBE (V) ต้องไม่ติดลบ")
    if values["vbe"] >= values["vcc"]:
        raise InputError("VBE (V) ต้องน้อยกว่า VCC (V)")

    return BiasInputs(
        mode=mode,
        vcc=values["vcc"],
        rc=values["rc"],
        beta=values["beta"],
        vbe=values["vbe"],
        r1=values.get("r1"),
        r2=values.get("r2"),
        rb=values.get("rb"),
        re=values.get("re"),
    )


def _require(value: float | None, name: str) -> float:
    """Return a field the mode needs, or fail loudly if it is missing."""
    if value is None:
        raise InputError(f"ข้อมูลภายในไม่ครบ: {FIELD_LABELS[name]}")
    return value


def _assemble(
    mode: str,
    ib: float,
    inputs: BiasInputs,
    *,
    vth: float | None = None,
    rth: float | None = None,
    cutoff_reason: str | None = None,
) -> dict[str, object]:
    """Turn a base current into the shared result dict for every mode.

    Voltages come out in V, currents in µA/mA so the template can print them
    without knowing any physics.
    """
    re = inputs.re or 0.0
    vth_v = vth if mode == MODE_DIVIDER else None
    rth_kohm = rth if mode == MODE_DIVIDER else None

    if ib <= 0.0:
        region = "cutoff"
        ib = ic = ie = 0.0
        ve = 0.0
        # No base current means no drop across RB, so a fixed/emitter base
        # sits at VCC. In a divider the base is held at VTH.
        vb = vth if vth is not None else inputs.vcc
        vc = inputs.vcc
        vce = inputs.vcc
        warnings: tuple[str, ...] = (
            cutoff_reason
            or "IB ≤ 0: ทรานซิสเตอร์อยู่ในช่วง Cutoff "
            "สมการ Forward-Active ใช้ไม่ได้ ค่าที่แสดงคือกรณีกระแสเป็นศูนย์",
        )
    else:
        ic = inputs.beta * ib
        ie = (inputs.beta + 1.0) * ib
        ve = ie * re * 1000.0
        vb = ve + inputs.vbe
        vc = inputs.vcc - ic * inputs.rc * 1000.0
        vce = vc - ve
        if vce <= VCE_SAT:
            region = "saturation"
            warnings = (
                f"VCE = {vce:.3f} V ไม่เกิน VCE_SAT = {VCE_SAT:.1f} V: "
                "ทรานซิสเตอร์อาจอยู่ในช่วง Saturation "
                "ค่า DC Bias จาก Forward-Active Approximation ไม่น่าเชื่อถือ",
            )
        else:
            region = "active"
            warnings = ()

    return {
        "mode": mode,
        "ib_ua": ib * 1e6,
        "ic_ma": ic * 1e3,
        "ie_ma": ie * 1e3,
        "vb_v": vb,
        "ve_v": ve,
        "vc_v": vc,
        "vce_v": vce,
        "vth_v": vth_v,
        "rth_kohm": rth_kohm,
        "region": region,
        "warnings": warnings,
    }


def divider_bias(inputs: BiasInputs) -> dict[str, object]:
    """Voltage-divider bias: IB = (VTH - VBE) / (RTH + (β+1)RE)."""
    r1 = _require(inputs.r1, "r1")
    r2 = _require(inputs.r2, "r2")
    re = _require(inputs.re, "re")

    vth = inputs.vcc * r2 / (r1 + r2)
    rth = r1 * r2 / (r1 + r2)  # kΩ

    if vth <= inputs.vbe:
        return _assemble(
            MODE_DIVIDER,
            0.0,
            inputs,
            vth=vth,
            rth=rth,
            cutoff_reason=(
                f"VTH = {vth:.3f} V ≤ VBE = {inputs.vbe:.2f} V: "
                "ทรานซิสเตอร์อยู่ในช่วง Cutoff สมการ Forward-Active ใช้ไม่ได้ "
                "ค่าที่แสดงคือกรณีกระแสเป็นศูนย์"
            ),
        )

    denominator = (rth + (inputs.beta + 1.0) * re) * 1000.0
    ib = (vth - inputs.vbe) / denominator
    return _assemble(MODE_DIVIDER, ib, inputs, vth=vth, rth=rth)


def fixed_bias(inputs: BiasInputs) -> dict[str, object]:
    """Fixed bias: IB = (VCC - VBE) / RB, emitter grounded."""
    rb = _require(inputs.rb, "rb")
    ib = (inputs.vcc - inputs.vbe) / (rb * 1000.0)
    return _assemble(MODE_FIXED, ib, inputs)


def emitter_bias(inputs: BiasInputs) -> dict[str, object]:
    """Emitter bias: IB = (VCC - VBE) / (RB + (β+1)RE)."""
    rb = _require(inputs.rb, "rb")
    re = _require(inputs.re, "re")
    denominator = (rb + (inputs.beta + 1.0) * re) * 1000.0
    ib = (inputs.vcc - inputs.vbe) / denominator
    return _assemble(MODE_EMITTER, ib, inputs)


HANDLERS: dict[str, Callable[[BiasInputs], dict[str, object]]] = {
    MODE_DIVIDER: divider_bias,
    MODE_FIXED: fixed_bias,
    MODE_EMITTER: emitter_bias,
}


def calculate(mode: str, inputs: BiasInputs) -> dict[str, object]:
    """Dispatch to the bias mode and return the shared result dict.

    An unknown mode is an error, never a silent fallback to the divider.
    """
    handler = HANDLERS.get(mode)
    if handler is None:
        raise InputError(
            f"โหมดไบอัสไม่รู้จัก: {mode} (รองรับ: divider, fixed, emitter)"
        )
    if inputs.mode != mode:
        raise InputError("ข้อมูลภายในไม่ตรงกัน: โหมดในฟอร์มกับโหมดที่คำนวณไม่ใช่ค่าเดียวกัน")
    return handler(inputs)
