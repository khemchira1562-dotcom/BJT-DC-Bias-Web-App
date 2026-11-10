# BJT DC Bias Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Flask multi-file web app that computes and displays the DC operating point of an NPN voltage-divider bias circuit with validation and region warnings.

**Architecture:** `dc_bias.py` holds pure engineering logic (parse + validate + solve). `app.py` maps HTTP GET/POST `/` to that module and renders a Jinja template. `tests/` covers math and HTTP independently.

**Tech Stack:** Python 3.13, Flask 3.x, Jinja2, `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-dc-bias-design.md`

## Global Constraints

- Resistances are entered in **kΩ** and converted to Ω inside `dc_bias.py`.
- `VCE_SAT = 0.3` V, declared as a module constant.
- `dc_bias.py` must not import Flask or touch HTML/HTTP.
- Thai UI copy, English symbols and units (`VCC`, `kΩ`, `mA`, `µA`).
- Only runtime dependency: Flask. Tests use stdlib `unittest`.
- No AC, transient, SPICE, or JavaScript frameworks.

## Review Focus

- `VBE ≥ VCC` or negative values must be rejected, not produce nonsense.
- Division by zero when `R1 + R2 == 0` must be impossible.
- Results must change when inputs change (no hardcoded numbers in the template).
- Cutoff must not display negative currents/voltages as if valid.
- Non-numeric or missing form fields must return a readable error, never HTTP 500.

---

### Task 1: Engineering module

**Files:**
- Create: `dc_bias.py`
- Test: `tests/test_dc_bias.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `VCE_SAT: float`, `FIELD_NAMES: tuple[str, ...]`, `InputError(ValueError)`,
  `BiasInputs`, `BiasResult`, `parse_inputs(raw: Mapping[str, str]) -> BiasInputs`,
  `calculate(inputs: BiasInputs) -> BiasResult`.

- [ ] **Step 1: Write failing tests** for reference values (`VCC=12, R1=100k, R2=22k,
  RC=2.2k, RE=1k, β=100, VBE=0.7` → VTH 2.164, RTH 18.033 kΩ, IC 1.2298 mA,
  VCE 8.052 V), cutoff (`R2=1k` → region `cutoff`), saturation (`RC=10k` →
  region `saturation`), and invalid inputs (`R1=0`, `beta=-1`, `vbe="abc"`,
  missing field, `vbe >= vcc`).
- [ ] **Step 2: Run** `.venv\Scripts\python -m unittest tests.test_dc_bias -v` → FAIL
  (module not found).
- [ ] **Step 3: Implement `dc_bias.py`** with the dataclasses, `parse_inputs`,
  and `calculate` from the design doc.
- [ ] **Step 4: Run tests** → PASS.

### Task 2: Flask app and template

**Files:**
- Create: `app.py`, `templates/index.html`, `static/style.css`, `requirements.txt`
- Test: `tests/test_web.py`

**Interfaces:**
- Consumes: `parse_inputs`, `calculate`, `InputError`, `FIELD_NAMES` from Task 1.
- Produces: Flask `app` object; routes `GET /` and `POST /`; Jinja filter `fmt`.

- [ ] **Step 1: Write failing HTTP tests**: GET `/` returns 200 and contains the
  seven field names; POST valid reference values returns 200 with `9.294`
  (VC) and `8.052` (VCE); POST `vcc=24` returns `21.294`; POST `r1=0` returns
  400 with a Thai error message.
- [ ] **Step 2: Run** `.venv\Scripts\python -m unittest tests.test_web -v` → FAIL.
- [ ] **Step 3: Implement** `app.py` (routes + `fmt` filter + `DEFAULT_VALUES`),
  `templates/index.html` (form + results + warnings), `static/style.css`.
- [ ] **Step 4: Run tests** → PASS.

### Task 3: Docs and verification

**Files:**
- Create: `README.md`, `AGENTS.md`, `.gitignore`, `docs/design-note.md`,
  `docs/validation.md`, `docs/reflection.md`

- [ ] **Step 1:** Write README with install/run/test commands, assumptions,
  `VCE_SAT`, and the reference result table.
- [ ] **Step 2:** Write `AGENTS.md` conventions and `.gitignore`
  (`.venv/`, `__pycache__/`, `*.pyc`, `.env`).
- [ ] **Step 3:** Record independent reference calculation in `docs/validation.md`.
- [ ] **Step 4:** Run full suite → all tests pass; start Flask and check `GET /`.
