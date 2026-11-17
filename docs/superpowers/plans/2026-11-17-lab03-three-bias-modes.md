# Lab 03 — สามโหมดไบอัส Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ต่อยอดเว็บ Flask เดิมให้เลือกได้สามโหมดไบอัส (Voltage Divider, Fixed, Emitter) โดยผลของ Divider ต้องเท่า Lab 02 เป๊ะ และตรวจรับผ่าน Browser ด้วย Playwright MCP

**Architecture:** แยก "สมการกระแสฐาน" ของแต่ละโหมดออกจาก "การประกอบผลลัพธ์" — `divider_bias/fixed_bias/emitter_bias` คำนวณ IB แล้วส่งเข้า `_assemble()` ตัวเดียวที่คืน `dict` คีย์ร่วม 8+ ตัว Route ทำหน้าที่อ่านฟอร์ม → `parse_inputs` → `calculate` → render เท่านั้น

**Tech Stack:** Python 3.13, Flask 3.1.3, Jinja2, stdlib `unittest` (27 ตัวเดิม), CSS ล้วน (ไม่มี JS), Playwright MCP สำหรับตรวจรับ

**Spec:** `docs/superpowers/specs/2026-11-17-lab03-three-bias-modes-design.md`

## Global Constraints

- `dc_bias.py` ห้าม import Flask — โมดูลนี้ต้องไม่รู้จัก HTML/HTTP
- `app.py` ห้ามคำนวณเอง: อ่านฟอร์ม → เรียก `dc_bias` → `render_template`
- `templates/` ห้ามมีสมการฟิสิกส์ มีแต่การแสดงผล
- `static/` เป็น CSS เท่านั้น **ห้ามเพิ่ม JavaScript**
- ค่าตัวต้านทานรับเป็น kΩ แล้วคูณ 1000 ครั้งเดียวใน `dc_bias.py`
- `VCE_SAT = 0.2` (V) ประกาศใน `dc_bias.py` เท่านั้น ห้าม hardcode ใน template
- ค่าที่ผิดต้อง raise `InputError` ข้อความภาษาไทย → HTTP 400 ห้ามปล่อยเป็น 500
- ออกนอก Forward-Active ต้องมี warning เสมอ (`IB ≤ 0` หรือ `VCE ≤ 0.2`)
- **ห้ามเพิ่ม unittest ใหม่** — คงไว้ 27 ตัว (8 + 19) และแก้เฉพาะวิธีอ่านค่า
- ห้ามเพิ่ม dependency นอกจาก Flask · ห้ามทำ SPICE / Load Line / AC / Bypass cap
- ข้อความ commit ภาษาอังกฤษรูปแบบ `type: summary` · push ผ่าน GitHub Desktop
- ค่าอ้างอิงบังคับ: A1 = 1.2299 mA / 8.0522 V, A2 = 1.1300 / 9.5140,
  A3 = 1.0263 / 8.7054, A4 = 0.9401 / 8.0328, A5 = HTTP 400

## Review Focus

กรณีที่สเปกไม่ได้เขียนตรง ๆ แต่คนใช้จะเจอแน่ — แต่ละข้อมีขั้นตรวจใน Task ที่ownsโค้ด (ไม่ใช่ unittest ใหม่ ตามข้อบังคับของใบงาน):

1. `mode="foo"` หรือไม่ส่ง `mode` มาเลย → ต้องได้ HTTP 400 พร้อมหน้าเว็บที่ยังแสดงฟอร์มครบ ไม่ใช่ 500 จาก `KeyError`
2. `RB = 0` หรือติดลบในโหมด fixed/emitter → 400 "RB (kΩ) ต้องมากกว่า 0" และต้องไม่มีผลรอบก่อนค้างอยู่
3. ช่องที่ไม่ใช้ของโหมดนั้นมีค่าขยะ (เช่น `r1="abc"` ขณะ `mode=fixed`) → ต้อง **ไม่** error เพราะโหมดนั้นไม่ใช้ค่านี้
4. Divider ที่ VTH ≤ VBE ต้องยังได้ VB = VTH (0.119 V) และ IC = 0 เหมือน Lab 02 ไม่ใช่ VB = 0.700 V
5. `VCE` เท่ากับ 0.2 V พอดี (ขอบ) → ต้องเข้าเงื่อนไข saturation เพราะใบงานเขียน `≤`
6. `mode` ถูกส่งมาแต่ช่องที่โหมดต้องใช้หายไป (เช่น fixed แต่ไม่มี `rb`) → 400 "กรุณากรอก RB (kΩ)"

---

### Task 1: โครงสร้างโหมดและการตรวจอินพุตใน `dc_bias.py`

**Files:**
- Modify: `dc_bias.py:1-107` (constants, `BiasInputs`, `parse_inputs`)
- Test: `tests/test_dc_bias.py` (แก้ mechanical), `tests/test_web.py` (เพิ่ม `mode` ใน REFERENCE)

**Interfaces:**
- Produces:
  - `VCE_SAT: float = 0.2`
  - `MODE_DIVIDER = "divider"`, `MODE_FIXED = "fixed"`, `MODE_EMITTER = "emitter"`
  - `MODES: tuple[str, ...] = ("divider", "fixed", "emitter")`
  - `MODE_LABELS: dict[str, str]` → `{"divider": "Voltage Divider Bias", "fixed": "Fixed Bias", "emitter": "Emitter Bias"}`
  - `MODE_FIELDS: dict[str, tuple[str, ...]]` → divider `("vcc","r1","r2","rc","re","beta","vbe")`, fixed `("vcc","rb","rc","beta","vbe")`, emitter `("vcc","rb","rc","re","beta","vbe")`
  - `FIELD_NAMES: tuple[str, ...] = ("vcc","r1","r2","rb","rc","re","beta","vbe")`
  - `FIELD_LABELS["rb"] = "RB (kΩ)"`
  - `BiasInputs(mode: str, vcc: float, rc: float, beta: float, vbe: float, r1: float|None = None, r2: float|None = None, rb: float|None = None, re: float|None = None)`
  - `parse_inputs(raw: Mapping[str, object]) -> BiasInputs`

- [ ] **Step 1: แก้ `tests/test_dc_bias.py` ให้ส่ง `mode` และอ่านผลแบบ dict**

`REFERENCE` เพิ่ม `"mode": "divider"` และเปลี่ยน `solve()` เป็น

```python
def solve(**overrides: float):
    values = {**REFERENCE, **overrides}
    return calculate(values["mode"], parse_inputs(values))
```

เปลี่ยนการอ่านค่าใน assertions (ค่าเลขและ delta เดิมทั้งหมด ห้ามผ่อน tolerance):

| เดิม | ใหม่ |
|---|---|
| `result.vth` | `result["vth_v"]` |
| `result.rth` | `result["rth_kohm"]` |
| `result.ib` (A) | `result["ib_ua"] / 1e6` |
| `result.ic` (A) | `result["ic_ma"] / 1e3` |
| `result.ie` (A) | `result["ie_ma"] / 1e3` |
| `result.vb` / `ve` / `vc` / `vce` | `result["vb_v"]` / `["ve_v"]` / `["vc_v"]` / `["vce_v"]` |
| `result.region` | `result["region"]` |
| `result.warnings` | `result["warnings"]` |

ใน `tests/test_web.py` เพิ่ม `"mode": "divider"` ใน `REFERENCE` (บรรทัดเดียว ไม่แก้ assertion อื่น)

- [ ] **Step 2: รัน tests ให้เห็นว่า fail**

Run: `.venv\Scripts\python -m unittest discover -s tests -v`
Expected: FAIL — `TypeError: calculate() takes 1 positional argument but 2 were given` (หรือ `KeyError` จาก `MODE_FIELDS` ถ้า import ไม่ผ่าน)

- [ ] **Step 3: เขียน constants / dataclass / `parse_inputs` ใน `dc_bias.py`**

ลำดับใน `parse_inputs`:

1. `mode = str(raw.get("mode", "")).strip()`
   - ว่าง → `raise InputError("กรุณาเลือกโหมดไบอัส (divider, fixed, emitter)")`
   - ไม่อยู่ใน `MODES` → `raise InputError(f"โหมดไบอัสไม่รู้จัก: {mode} (รองรับ: divider, fixed, emitter)")`
2. อ่านค่าด้วย `_to_float(raw.get(name, ""), FIELD_LABELS[name])` **เฉพาะ** `MODE_FIELDS[mode]`
3. ตรวจ `<= 0` สำหรับช่องที่โหมดใช้และเป็น kΩ/V (`r1, r2, rb, rc, re` ตามที่มีในโหมด) → `"{label} ต้องมากกว่า 0"`
4. `beta <= 0` → `"β (Beta) ต้องมากกว่า 0"` · `vbe < 0` → `"VBE (V) ต้องไม่ติดลบ"` · `vbe >= vcc` → `"VBE (V) ต้องน้อยกว่า VCC (V)"`
5. คืน `BiasInputs` โดยช่องที่ไม่ใช้ของโหมดเป็น `None`

คง `_to_float` เดิมทั้งหมด (ข้อความ "กรุณากรอก / ต้องเป็นตัวเลข / ต้องเป็นค่าจำกัด" ต้องไม่เปลี่ยน เพราะ web tests assert ข้อความเหล่านี้)

- [ ] **Step 4: รัน tests**

Run: `.venv\Scripts\python -m unittest discover -s tests -v`
Expected: ยัง FAIL เฉพาะ tests ที่เรียก `calculate` (ยังไม่ได้เขียน Task 2) — ส่วน validation tests ต้องผ่าน

- [ ] **Step 5: Commit**

```bash
git add dc_bias.py tests/test_dc_bias.py tests/test_web.py
git commit -m "refactor: add bias mode plumbing and per-mode input validation"
```

---

### Task 2: สมการสามโหมด + `_assemble` + dispatch

**Files:**
- Modify: `dc_bias.py` (แทน `BiasResult` และ `calculate` เดิมทั้งบล็อก)

**Interfaces:**
- Consumes: `BiasInputs`, `MODE_FIELDS`, `MODES`, `VCE_SAT` จาก Task 1
- Produces:
  - `divider_bias(inputs: BiasInputs) -> dict[str, object]`
  - `fixed_bias(inputs: BiasInputs) -> dict[str, object]`
  - `emitter_bias(inputs: BiasInputs) -> dict[str, object]`
  - `calculate(mode: str, inputs: BiasInputs) -> dict[str, object]`
  - dict คีย์: `mode, ib_ua, ic_ma, ie_ma, vb_v, ve_v, vc_v, vce_v, vth_v, rth_kohm, region, warnings`

- [ ] **Step 1: เขียน `_assemble`**

```python
def _assemble(
    mode: str,
    ib: float,
    inputs: BiasInputs,
    *,
    vth: float | None = None,
    rth: float | None = None,
) -> dict[str, object]:
```

ขั้นตอน:

1. ถ้า `ib <= 0` → cutoff: `ib = ic = ie = 0.0`, `ve = 0.0`, `vc = vcc`, `vce = vcc`,
   `vb = vth if mode == MODE_DIVIDER and vth is not None else vcc`
   warning: `"IB ≤ 0: ทรานซิสเตอร์อยู่ในช่วง Cutoff สมการ Forward-Active ใช้ไม่ได้ ค่าที่แสดงคือกรณีกระแสเป็นศูนย์"`
2. ไม่งั้นคำนวณ `ic = beta*ib`, `ie = (beta+1)*ib`, `ve = ie*re*1000.0`
   (`re = inputs.re or 0.0` เพื่อให้ fixed ใช้ 0), `vb = ve + vbe`,
   `vc = vcc - ic*rc*1000.0`, `vce = vc - ve`
3. ถ้า `vce <= VCE_SAT` → `region = "saturation"` + warning
   `f"VCE = {vce:.3f} V ไม่เกิน VCE_SAT = {VCE_SAT:.1f} V: ทรานซิสเตอร์อาจอยู่ในช่วง Saturation ค่า DC Bias จาก Forward-Active Approximation ไม่น่าเชื่อถือ"`
4. คืน dict โดยแปลงหน่วยเป็น µA/mA ตามคีย์ (`ib_ua = ib*1e6`, `ic_ma = ic*1e3`, `ie_ma = ie*1e3`) และ `warnings` เป็น `tuple[str, ...]`

- [ ] **Step 2: เขียนสามฟังก์ชันโหมด (แต่ละตัวมีแค่บรรทัด IB ต่างกัน)**

```
divider_bias : vth = vcc*r2/(r1+r2); rth = r1*r2/(r1+r2)
               vth <= vbe -> _assemble(..., ib=0.0, vth=vth, rth=rth)
               ib = (vth - vbe) / ((rth + (beta+1)*re) * 1000.0)
fixed_bias   : ib = (vcc - vbe) / (rb * 1000.0)
emitter_bias : ib = (vcc - vbe) / ((rb + (beta+1)*re) * 1000.0)
```

อ่านค่าที่จำเป็นผ่าน helper `_require(value: float | None, name: str) -> float` ที่
`raise InputError(f"ข้อมูลภายในไม่ครบ: {name}")` ถ้าเป็น `None`

- [ ] **Step 3: เขียน `calculate`**

```python
HANDLERS = {MODE_DIVIDER: divider_bias, MODE_FIXED: fixed_bias, MODE_EMITTER: emitter_bias}

def calculate(mode: str, inputs: BiasInputs) -> dict[str, object]:
    handler = HANDLERS.get(mode)
    if handler is None:
        raise InputError(f"โหมดไบอัสไม่รู้จัก: {mode} (รองรับ: divider, fixed, emitter)")
    return handler(inputs)
```

ลบ `BiasResult` เดิมออก (ไม่มีใครใช้แล้ว) — ถ้าเหลือที่อ้างถึงให้ลบด้วย

- [ ] **Step 4: รัน tests ทั้ง 27 ตัว**

Run: `.venv\Scripts\python -m unittest discover -s tests -v`
Expected: `Ran 27 tests` … `OK`

- [ ] **Step 5: ตรวจค่าอ้างอิง A1–A4 ด้วยการเรียกฟังก์ชันตรง (ไม่ commit ไฟล์ใด)**

```bash
.venv\Scripts\python -c "from dc_bias import *; \
print(calculate('divider', parse_inputs({'mode':'divider','vcc':12,'r1':100,'r2':22,'rc':2.2,'re':1,'beta':100,'vbe':0.7}))); \
print(calculate('fixed', parse_inputs({'mode':'fixed','vcc':12,'rb':1000,'rc':2.2,'beta':100,'vbe':0.7}))); \
print(calculate('emitter', parse_inputs({'mode':'emitter','vcc':12,'rb':1000,'rc':2.2,'re':1,'beta':100,'vbe':0.7}))); \
print(calculate('emitter', parse_inputs({'mode':'emitter','vcc':12,'rb':1000,'rc':2.2,'re':2,'beta':100,'vbe':0.7})))"
```

Expected: `ic_ma` = 1.2299 / 1.1300 / 1.0263 / 0.9401 และ `vce_v` = 8.0522 / 9.5140 / 8.7054 / 8.0328 (±0.0005)

- [ ] **Step 6: Commit**

```bash
git add dc_bias.py
git commit -m "feat: add fixed and emitter bias equations with shared result dict"
```

---

### Task 3: Route และฟอร์มเลือกโหมด

**Files:**
- Modify: `app.py` (ทั้งไฟล์), `templates/index.html` (ทั้งไฟล์), `static/style.css` (เพิ่มท้ายไฟล์)

**Interfaces:**
- Consumes: `MODE_FIELDS`, `MODES`, `MODE_LABELS`, `VCE_SAT`, `FIELD_NAMES`, `calculate`, `parse_inputs`, `InputError`
- Produces: context ของ template = `values, result, error, region_labels, mode_labels, active_fields, vce_sat`

- [ ] **Step 1: แก้ `app.py`**

```python
def _render(values, result=None, error=None, status=200):
    display_mode = values.get("mode", "") if values.get("mode", "") in MODES else MODE_DIVIDER
    return (
        render_template(
            "index.html",
            values=values,
            result=result,
            error=error,
            region_labels=REGION_LABELS,
            mode_labels=MODE_LABELS,
            active_fields=MODE_FIELDS[display_mode],
            vce_sat=VCE_SAT,
        ),
        status,
    )
```

- `GET` → `return _render(DEFAULT_VALUES)` (Flask รับ `(response, status)` ได้เลย)
- `POST` → `values = {"mode": request.form.get("mode", "").strip(), **{name: request.form.get(name, "").strip() for name in FIELD_NAMES}}`
  → `try: result = calculate(values["mode"], parse_inputs(values))` → `except InputError: return _render(values, error=str(exc), status=400)`
- `DEFAULT_VALUES` เพิ่ม `"mode": "divider"` และ `"rb": "1000"` (1 MΩ สำหรับ A2–A4)

- [ ] **Step 2: แก้ `templates/index.html`**

- `<title>` และ eyebrow/footer เป็น **LAB 03**; `<p class="sub">` ระบุสามโหมด
- ก่อน `.grid` ใส่ dropdown เต็มแถว:

```html
<label class="mode-row">โหมดไบอัส
  <select name="mode">
    {% for mode in mode_labels %}
    <option value="{{ mode }}" {% if mode == values.mode %}selected{% endif %}>{{ mode_labels[mode] }}</option>
    {% endfor %}
  </select>
</label>
```

- ทุกช่องอินพุตได้คลาส `field` และเพิ่ม `field--unused` เมื่อชื่อช่องไม่อยู่ใน `active_fields`
  เช่น `<label class="field {% if 'rb' not in active_fields %}field--unused{% endif %}">`
  ลำดับช่อง: VCC, RB, R1, R2, RC, RE, β, VBE
- หัวข้อผลลัพธ์: `2. DC Bias Results — {{ mode_labels[result.mode] }}`
- ตารางอ่านจาก dict: `{{ result.vb_v|fmt }}`, `{{ result.ve_v|fmt }}`, `{{ result.vc_v|fmt }}`,
  `{{ result.vce_v|fmt }}`, `{{ result.ib_ua|fmt }} µA`, `{{ result.ic_ma|fmt }} mA`,
  `{{ result.ie_ma|fmt }} mA`
- บรรทัดสรุป:

```html
<p class="muted">
  {% if result.mode == 'divider' %}VTH = {{ result.vth_v|fmt }} V · RTH = {{ result.rth_kohm|fmt }} kΩ · {% endif %}VCE_SAT = {{ vce_sat|fmt(1) }} V
</p>
```

- warning loop และ footnote คงเดิม (footnote ต้องไม่กล่าวถึงโหมดเดียว)
- error block คงเดิม — `result` เป็น `None` ทำให้ไม่มีส่วนผลลัพธ์ค้าง

- [ ] **Step 3: เพิ่ม CSS ท้าย `static/style.css`**

```css
.field--unused { display: none; }
.mode-row { grid-column: 1 / -1; }
```

ถ้า `.grid` เดิมไม่ใช่ grid ที่รองรับ `1 / -1` ให้ใช้ `width: 100%` แทนและบันทึกเหตุผลใน commit message body

- [ ] **Step 4: รัน tests**

Run: `.venv\Scripts\python -m unittest discover -s tests -v`
Expected: `Ran 27 tests` … `OK` (web tests ยังส่ง `mode=divider` จาก REFERENCE)

- [ ] **Step 5: ตรวจกรณีขอบด้วย Flask test client (Review Focus 1, 2, 3, 6)**

```bash
.venv\Scripts\python -c "from app import app; c=app.test_client(); \
print('unknown', c.post('/', data={'mode':'foo','vcc':'12','rc':'2.2','beta':'100','vbe':'0.7'}).status_code); \
print('nomode', c.post('/', data={'vcc':'12','rc':'2.2','beta':'100','vbe':'0.7'}).status_code); \
print('rb0', c.post('/', data={'mode':'fixed','vcc':'12','rb':'0','rc':'2.2','beta':'100','vbe':'0.7'}).status_code); \
print('junk-unused', c.post('/', data={'mode':'fixed','vcc':'12','rb':'1000','r1':'abc','rc':'2.2','beta':'100','vbe':'0.7'}).status_code); \
print('missing-rb', c.post('/', data={'mode':'emitter','vcc':'12','rc':'2.2','re':'1','beta':'100','vbe':'0.7'}).status_code)"
```

Expected: `unknown 400`, `nomode 400`, `rb0 400`, `junk-unused 200`, `missing-rb 400`
ถ้าข้อใดไม่ตรง ให้แก้ `parse_inputs`/route ก่อนไปต่อ

- [ ] **Step 6: Commit**

```bash
git add app.py templates/index.html static/style.css
git commit -m "feat: add bias mode selector and mode-aware result rendering"
```

---

### Task 4: ตรวจรับ A1–A5 ผ่าน Browser (Playwright MCP)

**Files:**
- ไม่แก้ไฟล์โค้ด — ผลลัพธ์ของ task นี้คือค่าที่อ่านได้จริงสำหรับใส่ใน `docs/validation.md` (Task 5)

**Interfaces:**
- Consumes: เว็บที่รันจาก Task 3

- [ ] **Step 1: เปิด Flask**

Run (background): `.venv\Scripts\python -m flask --app app run --port 5000`
Expected: HTTP 200 ที่ `http://127.0.0.1:5000/`

- [ ] **Step 2: ตรวจ A1 (divider, ต้องเท่า Lab 02)**

Playwright: เปิดหน้า → เลือก `divider` → VCC 12, R1 100, R2 22, RC 2.2, RE 1, β 100, VBE 0.7 → Calculate
Expected บนหน้าเว็บ: IC `1.230 mA`, VCE `8.052 V`, VB `1.942 V`, region `Active`

- [ ] **Step 3: ตรวจ A2 (fixed, RB = 1000 kΩ)**

Expected: IC `1.130 mA`, VCE `9.514 V`, VE `0.000 V`, VB `0.700 V`, ไม่แสดงช่อง R1/R2/RE

- [ ] **Step 4: ตรวจ A3 / A4 (emitter, RE = 1 kΩ แล้ว 2 kΩ)**

Expected: A3 IC `1.026 mA`, VCE `8.705 V` · A4 IC `0.940 mA`, VCE `8.033 V`
ต้องเห็นว่า IC ของ A4 **น้อยกว่า** A3 ตามที่ทำนายไว้

- [ ] **Step 5: ตรวจ A5 (fixed, RB = 0)**

Expected: หน้าเดิมกลับมา ไม่มี HTTP error page, มีข้อความ `RB (kΩ) ต้องมากกว่า 0`,
**ไม่มี** ตารางผลลัพธ์ และไม่มีค่า IC ของรอบก่อน

- [ ] **Step 6: ทวนเอง 1 กรณี (emitter, RB = 470 kΩ, RE = 1 kΩ)**

Expected: IB `19.790 µA`, IC `1.979 mA`, VE `1.999 V`, VCE `5.647 V`
(คำนวณมือ: `11.3/((470+101)·1000) = 19.79 µA`)

- [ ] **Step 7: ตรวจ Review Focus 4 และ 5**

- divider R2 = 1 kΩ → region `Cutoff`, IC `0.000 mA`, VB `0.119 V`, มี warning
- emitter ที่ทำให้ VCE ลงมาแตะ 0.2 พอดี (ปรับ RC ให้ได้ `vce_v ≈ 0.200`) → ต้องขึ้น `Saturation` + warning

- [ ] **Step 8: จดค่าที่อ่านได้จริง**

บันทึกเป็นตารางชั่วคราว (ในแชทหรือ scratch) สำหรับ Task 5 — **ห้ามเดาตัวเลข**
ถ้ากรณีใดรันไม่ได้จริง ให้บันทึก `NOT RUN` พร้อมเหตุผล

---

### Task 5: เอกสาร + governance + ไฟล์ MCP แล้ว commit

**Files:**
- Modify: `README.md`, `docs/validation.md`, `docs/design-note.md`, `AGENTS.md`, `.gitignore`
- Create: `opencode.json` (เขียนทับของเดิมแบบ portable)

**Interfaces:**
- Consumes: ค่าที่อ่านได้จริงจาก Task 4

- [ ] **Step 1: `README.md`**

- หัวเรื่องเป็น Lab 03, ระบุสามโหมด
- ตารางช่องอินพุตต่อโหมด (จาก `MODE_FIELDS`)
- สมการสามชุดตาม §7.5 ของ spec
- `VCE_SAT = 0.2 V` และเงื่อนไข warning (`IB ≤ 0`, `VCE ≤ 0.2`)
- วิธีตรวจผ่านเบราว์เซอร์ (รัน Flask + ใช้ Playwright MCP) และหมายเหตุว่า
  ไม่มี unittest ของโหมดใหม่เพราะใบงานกำหนดให้ตรวจผ่าน Browser
- ค่าอ้างอิง A1–A5

- [ ] **Step 2: `docs/validation.md`**

เพิ่มหัวข้อ "Lab 03" ประกอบด้วย

1. ค่าอ้างอิงอิสระ A1–A5 พร้อม derivation ย่อ (IB จากสมการแต่ละโหมด)
2. ตาราง "ผลจากเว็บ" ที่คัดลอกมาจาก Task 4 (ระบุวันที่ + วิธีตรวจ = Playwright MCP)
3. กรณีทวนมือเอง (RB = 470 kΩ) พร้อมเลขที่คำนวณมือ
4. Test log: `Ran 27 tests … OK` (ของเดิม)
5. หมายเหตุว่าทำไมไม่มี unittest ของโหมดใหม่ (ใบงานห้าม/ไม่ต้อง)
6. เหตุผลที่เปลี่ยน `VCE_SAT` 0.3 → 0.2

- [ ] **Step 3: `docs/design-note.md` และ `AGENTS.md`**

- design-note: เพิ่มหัวข้อย่อย "Lab 03: การแยก `_assemble`" + เหตุผล D1/D2 + แก้ข้อความ 0.3 V เป็น 0.2 V พร้อมหมายเหตุว่าเปลี่ยนตามใบงาน
- AGENTS.md: `VCE_SAT = 0.3 V` → `VCE_SAT = 0.2 V` ( Lab 03 )

- [ ] **Step 4: `.gitignore` และ `opencode.json`**

- เพิ่ม `.playwright-mcp/` ใน `.gitignore`
- เขียน `opencode.json` เวอร์ชัน portable (ไม่ใส่ `environment`):

```json
{
  "mcp": {
    "servers": {
      "playwright": {
        "type": "local",
        "command": ["npx", "-y", "@playwright/mcp@latest", "--browser", "chrome", "--isolated"]
      }
    }
  }
}
```

> ถ้า MCP ใน session นี้ยังต้องใช้ `environment.PATH` ให้เขียนไฟล์ portable **หลัง** การตรวจ Task 4 เสร็จเท่านั้น แล้วจดไว้ใน README ว่าต้องมี Node อยู่ใน PATH

- [ ] **Step 5: ตรวจว่าไม่มีอะไรค้างและ tests ยังผ่าน**

```bash
git status --short --branch
.venv\Scripts\python -m unittest discover -s tests -v
```

Expected: 27 tests OK และไม่มีไฟล์ `.pyc`/`.playwright-mcp/` ถูก track

- [ ] **Step 6: Commit**

```bash
git add README.md docs/validation.md docs/design-note.md AGENTS.md .gitignore opencode.json
git commit -m "docs: document three bias modes and lab 03 browser validation"
```

- [ ] **Step 7: ส่งมอบ**

บอกผู้ใช้ให้กด **Push origin** ใน GitHub Desktop แล้วรายงาน commit SHA
(CLI push ไม่มี credential) — ระบุ SHA สุดท้ายสำหรับส่ง Moodle
