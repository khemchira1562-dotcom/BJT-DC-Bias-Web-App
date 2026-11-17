"""Flask application for the BJT DC Bias calculator.

Routes only: read the form, delegate to dc_bias, render the template.
"""

from __future__ import annotations

from flask import Flask, render_template, request

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
}

REGION_LABELS = {
    "active": "Active",
    "cutoff": "Cutoff",
    "saturation": "Saturation",
}


@app.template_filter("fmt")
def fmt(value: float, digits: int = 3) -> str:
    """Format a number for display with a fixed number of decimals."""
    return f"{float(value):.{digits}f}"


def _display_mode(values: dict[str, str]) -> str:
    """Mode used to lay out the form; unknown modes fall back to the divider."""
    mode = values.get("mode", "")
    return mode if mode in MODES else MODE_DIVIDER


def _render(
    values: dict[str, str],
    *,
    result: dict[str, object] | None = None,
    error: str | None = None,
    status: int = 200,
):
    display_mode = _display_mode(values)
    return (
        render_template(
            "index.html",
            values=values,
            result=result,
            error=error,
            region_labels=REGION_LABELS,
            mode_labels=MODE_LABELS,
            display_mode=display_mode,
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
    values = {"mode": request.form.get("mode", "").strip()}
    values.update({name: request.form.get(name, "").strip() for name in FIELD_NAMES})

    # Switching mode must not silently calculate from a field the user could
    # not see: "แสดงช่องของโหมดนี้" only re-renders the form.
    if request.form.get("action") == "layout":
        return _render(values)

    try:
        result = calculate(values["mode"], parse_inputs(values))
    except InputError as exc:
        return _render(values, error=str(exc), status=400)

    return _render(values, result=result)


if __name__ == "__main__":
    app.run(debug=True)
