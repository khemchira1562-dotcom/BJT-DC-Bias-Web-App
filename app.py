"""Flask application for the Lab 03 bias calculator + Lab 04 CE simulator.

Routes only: read the form, delegate to dc_bias or spice_engine, render the
template. No physics or simulation parsing happens in this module.
"""

from __future__ import annotations

from flask import Flask, render_template, request

from charts import bode_svg, waveform_svg
from dc_bias import (
    FIELD_NAMES,
    MODE_DIVIDER,
    MODE_FIELDS,
    MODE_LABELS,
    MODES,
    VCE_SAT,
    InputError,
    calculate,
    parse_inputs,
)
from spice_engine import (
    DEFAULT_MODEL as SPICE_DEFAULT_MODEL,
    FIELD_NAMES as SPICE_FIELD_NAMES,
    MODE_LABELS as ANALYSIS_LABELS,
    MODES as ANALYSIS_MODES,
    SpiceError,
    run_simulation,
)

app = Flask(__name__)

DEFAULT_VALUES = {
    "mode": MODE_DIVIDER,
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rb": "1000",
    "rc": "2.2",
    "re": "1",
    "beta": "100",
    "vbe": "0.7",
    "analysis": "dc",
    "rl": "10",
    "cin_uf": "10",
    "cout_uf": "10",
    "amplitude_mv": "10",
    "frequency_khz": "1",
    "model": SPICE_DEFAULT_MODEL,
    "fmin_hz": "10",
    "fmax_hz": "1000000",
    "tran_stop_ms": "5",
}

FORM_FIELDS = tuple(
    dict.fromkeys(("mode", "analysis", *FIELD_NAMES, *SPICE_FIELD_NAMES))
)

REGION_LABELS = {
    "active": "Active",
    "cutoff": "Cutoff",
    "saturation": "Saturation",
}


@app.template_filter("fmt")
def fmt(value: float, digits: int = 3) -> str:
    """Format a number for display with a fixed number of decimals."""
    return f"{float(value):.{digits}f}"


@app.template_filter("bode_svg")
def bode_filter(series: list[dict[str, float]]) -> str:
    """Presentation filter: parsed AC numbers → inline SVG."""
    return bode_svg(series)


@app.template_filter("waveform_svg")
def waveform_filter(series: list[dict[str, float]]) -> str:
    """Presentation filter: parsed transient numbers → inline SVG."""
    return waveform_svg(series)


def _display_mode(values: dict[str, str]) -> str:
    """Mode used to lay out the form; unknown modes fall back to the divider."""
    mode = values.get("mode", "")
    return mode if mode in MODES else MODE_DIVIDER


def _display_analysis(values: dict[str, str]) -> str:
    analysis = values.get("analysis", "").strip().lower()
    return analysis if analysis in ANALYSIS_MODES else ANALYSIS_MODES[0]


def _render(
    values: dict[str, str],
    *,
    result: dict[str, object] | None = None,
    spice_result: dict[str, object] | None = None,
    error: str | None = None,
    status: int = 200,
):
    display_mode = _display_mode(values)
    return (
        render_template(
            "index.html",
            values=values,
            result=result,
            spice_result=spice_result,
            error=error,
            region_labels=REGION_LABELS,
            mode_labels=MODE_LABELS,
            analysis_labels=ANALYSIS_LABELS,
            spice_default_model=SPICE_DEFAULT_MODEL,
            display_mode=display_mode,
            display_analysis=_display_analysis(values),
            active_fields=MODE_FIELDS[display_mode],
            vce_sat=VCE_SAT,
        ),
        status,
    )


@app.get("/")
def index():
    return _render(DEFAULT_VALUES)


@app.post("/")
def submit():
    values = {name: request.form.get(name, "").strip() for name in FORM_FIELDS}
    action = request.form.get("action", "calculate")

    # Switching mode must not silently calculate from a field the user could
    # not see: "แสดงช่องของโหมดนี้" only re-renders the form.
    if action == "layout":
        return _render(values)

    if action == "simulate":
        try:
            spice_result = run_simulation(values)
        except SpiceError as exc:
            return _render(values, error=str(exc), status=400)
        return _render(values, spice_result=spice_result)

    try:
        result = calculate(values["mode"], parse_inputs(values))
    except InputError as exc:
        return _render(values, error=str(exc), status=400)

    return _render(values, result=result)


if __name__ == "__main__":
    app.run(debug=True)
