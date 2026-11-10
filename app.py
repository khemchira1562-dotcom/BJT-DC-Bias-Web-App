"""Flask application for the BJT DC Bias calculator.

Routes only: read the form, delegate to dc_bias, render the template.
"""

from __future__ import annotations

from flask import Flask, render_template, request

from dc_bias import FIELD_NAMES, InputError, calculate, parse_inputs

app = Flask(__name__)

DEFAULT_VALUES = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
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


@app.get("/")
def index():
    return render_template(
        "index.html",
        values=DEFAULT_VALUES,
        result=None,
        error=None,
        region_labels=REGION_LABELS,
    )


@app.post("/")
def submit():
    values = {name: request.form.get(name, "").strip() for name in FIELD_NAMES}
    try:
        result = calculate(parse_inputs(values))
    except InputError as exc:
        return (
            render_template(
                "index.html",
                values=values,
                result=None,
                error=str(exc),
                region_labels=REGION_LABELS,
            ),
            400,
        )

    return render_template(
        "index.html",
        values=values,
        result=result,
        error=None,
        region_labels=REGION_LABELS,
    )


if __name__ == "__main__":
    app.run(debug=True)
