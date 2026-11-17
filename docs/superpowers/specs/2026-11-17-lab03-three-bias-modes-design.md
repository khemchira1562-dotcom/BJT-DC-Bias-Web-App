# Design — Lab 03: สามโหมดไบอัส + การตรวจผลผ่าน Browser

วันที่: 2026-11-17
สถานะ: อนุมัติแล้ว 2026-11-17 (ผู้ใช้เลือก D1=A, D2=A และยึด 27 tests ตามบรีฟ)

## 1. เจตนา และเหตุผล

Lab 02 ส่งเว็บ Flask ที่คำนวณ DC Bias ได้โหมดเดียว (Voltage Divider) และมี
unittest 27 ตัวผ่านหมด Lab 03 ต้องการต่อยอดเว็บเดิม **ไม่ใช่ทำใหม่** ให้เลือก
วงจรได้สามแบบ (Fixed Bias, Emitter Bias, Voltage Divider) โดยที่

- เลือก Divider ด้วยค่าเดิมแล้ว **ผลต้องเท่า Lab 02 เป๊ะ** (IC 1.2299 mA,
  VCE 8.0522 V) เพื่อพิสูจน์ว่า refactor ไม่ทำให้ผลเดิมเพี้ยน
- ผลลัพธ์ของทั้งสามโหมดมี **รูปทรงเดียวกัน** เพื่อให้ template เดียว render ได้
  โดยไม่ต้องเขียน branch ตามโหมด
- ตรวจรับงานด้วย Browser (Playwright MCP) ตามตาราง A1–A5 ของใบงาน

เหตุผลเชิงวิศวกรรม: การเพิ่มโหมดคือการแยก "สมการกระแสฐาน" ออกจาก "การประกอบ
ผลลัพธ์" ถ้าแยกถูก จุดที่ต่างกันมีแค่บรรทัดคำนวณ IB เท่านั้น

## 2. Goals

1. `dc_bias.py` มี `divider_bias()`, `fixed_bias()`, `emitter_bias()` แยกกัน
   และ `calculate(mode, inputs)` เป็นตัว dispatch
2. ทุกฟังก์ชันโหมดคืน `dict` คีย์ร่วมชุดเดียวกัน
3. โหมดไม่รู้จัก / ไม่ส่งโหมด → `InputError` (HTTP 400) **ไม่เดาเป็น Divider**
4. ฟอร์มมี dropdown เลือกโหมด และแสดงเฉพาะช่องที่โหมดนั้นใช้
5. `VCE_SAT = 0.2 V` ตามใบงาน พร้อม warning เมื่อออกนอก Forward-Active
6. ผลของ Divider เท่า Lab 02 ทุกหลัก
7. เอกสาร: README สามโหมด + `docs/validation.md` ตาราง A1–A5

## 3. Non-goals

- ไม่ทำ SPICE / ngspice integration
- ไม่ทำ DC Load Line หรือจุด Q บนกราฟ
- ไม่ทำ AC analysis, transient, bypass capacitor
- ไม่เขียนสคริปต์ Playwright/Python สำหรับ automate การตรวจ (ตรวจผ่าน MCP)
- ไม่เขียน unittest ใหม่ (ใบงานระบุชัด) — เก็บ 27 ตัวเดิมให้ผ่าน
  และแก้เฉพาะรูปแบบการอ่านค่าแบบ mechanical (§7.10, §11.1)
- ไม่แตะ `docs/reflection.md` ของ Lab 02 (จะอัปเดตแยกถ้าอาจารย์สั่ง)

## 4. Anti-goals (ถือว่างานนี้ล้มเหลวถ้าเกิด)

- ผล Divider เปลี่ยนจาก Lab 02 แม้แต่ในหลักที่สาม
- โหมดที่ไม่รู้จักถูกตีความเป็น Divider เงียบ ๆ
- ค่าที่ผิดทำให้หน้าเว็บ 500 แทนที่จะเป็น 400 + ข้อความไทย
- ผลรอบก่อนค้างอยู่บนหน้าจอพร้อม error รอบใหม่
- เพิ่ม dependency ใหม่ (ต้องใช้ Flask เท่านั้น)

## 5. Constraints

- `dc_bias.py` ห้าม import Flask
- `app.py` ห้ามคำนวณเอง — อ่านฟอร์ม → เรียก `dc_bias` → render
- `templates/` ห้ามมีสมการฟิสิกส์
- `static/` เป็น CSS เท่านั้น ไม่มี JavaScript (จึงสลับช่องด้วย server-render)
- ค่าตัวต้านทานรับเป็น kΩ แล้วคูณ 1000 ครั้งเดียวใน `dc_bias.py`
- ข้อความ error/warning เป็นภาษาไทย
- Commit ผ่าน GitHub Desktop, ข้อความอังกฤษรูปแบบ `type: summary`

## 6. ทางเลือกที่พิจารณา

### D1 — รูปแบบผลลัพธ์

| ทางเลือก | ข้อดี | ข้อเสีย |
|---|---|---|
| **A: ทุกโหมดคืน `dict`** (เลือก) | ตรงใบงานตัวอักษร ("ส่งผลเป็น dict ที่ใช้คีย์ร่วมกัน เช่น `vb_v, ve_v, vc_v, vce_v, ic_ma`"), template เขียนครั้งเดียว, route ไม่ต้องรู้จัก dataclass | ต้องแก้ 19 tests แบบ mechanical (`.ic` → `["ic_ma"]`) |
| B: คง `BiasResult` + `as_dict()` | ไม่ต้องแตะ tests เลย | ไม่ตรงถ้อยคำใบงาน เสี่ยงคะแนนหมวด "โครงสร้างและ Python" (3 คะแนน) |
| C: dataclass ที่รองรับ `result["key"]` | ใช้ได้ทั้งสองแบบ | ผสมสอง API ในวัตถุเดียว อ่านยาก ผิดหลัก "อย่างง่าย" |

**เลือก A** — ค่าเลขใน assertions ไม่เปลี่ยนเลย เปลี่ยนแค่วิธีอ่านค่า

### D2 — ฟอร์มสลับช่องตามโหมด (ห้าม JS)

| ทางเลือก | ข้อดี | ข้อเสีย |
|---|---|---|
| **A: render ทุกช่อง + ซ่อนด้วยคลาส CSS** (เลือก) | ค่าที่กรอกไว้ไม่หาย, กด Calculate ครั้งเดียว, ไม่ต้อง JS | HTML มีช่องที่มองไม่เห็น (แต่ยัง submit) |
| B: render เฉพาะช่องของโหมด | HTML สะอาด | สลับโหมดแล้วค่าของโหมดอื่นหาย ต้องกรอกใหม่ |
| C: ใช้ JavaScript toggle | UX ลื่นที่สุด | ผิดกติกา `static/` ของ repo |

**เลือก A** — ช่องที่ซ่อนยังถูก submit แต่ `parse_inputs` อ่านเฉพาะช่องที่โหมด
นั้นต้องใช้ จึงไม่มีผลข้างเคียง

## 7. การออกแบบ

### 7.1 ค่าคงที่และรายชื่อโหมด

```python
VCE_SAT = 0.2  # V (Lab 03)

MODE_DIVIDER = "divider"
MODE_FIXED = "fixed"
MODE_EMITTER = "emitter"
MODES = (MODE_DIVIDER, MODE_FIXED, MODE_EMITTER)

MODE_LABELS = {
    "divider": "Voltage Divider Bias",
    "fixed": "Fixed Bias",
    "emitter": "Emitter Bias",
}
```

### 7.2 ช่องอินพุตที่แต่ละโหมดใช้

| ช่อง | divider | fixed | emitter |
|---|---|---|---|
| vcc | ✓ | ✓ | ✓ |
| r1 | ✓ | – | – |
| r2 | ✓ | – | – |
| rb | – | ✓ | ✓ |
| rc | ✓ | ✓ | ✓ |
| re | ✓ | – | ✓ |
| beta | ✓ | ✓ | ✓ |
| vbe | ✓ | ✓ | ✓ |

`FIELD_LABELS` เพิ่ม `"rb": "RB (kΩ)"` และ `MODE_FIELDS: dict[str, tuple[str, ...]]`
เก็บตารางนี้ไว้ที่เดียว ทั้ง `parse_inputs` และ template ใช้ร่วมกัน

### 7.3 `BiasInputs`

คงเป็น dataclass ที่มีทุกช่อง แต่ช่องที่ไม่ใช้ของโหมดนั้นเป็น `None`:

```python
@dataclass(frozen=True)
class BiasInputs:
    mode: str
    vcc: float
    rc: float
    beta: float
    vbe: float
    r1: float | None = None
    r2: float | None = None
    rb: float | None = None
    re: float | None = None
```

เหตุผล: `divider_bias()` ต้องรู้ว่า `r1/r2` มีค่าแน่ ๆ — ใช้ `assert` หรือ
fallback ไม่ได้ ฟังก์ชันโหมดจึงอ่านค่าผ่าน helper `_require(value, name)`
ที่ raise `InputError` ถ้าเป็น `None` (กัน bug ภายใน) — แต่ในทางปฏิบัติ
`parse_inputs` รับประกันแล้วว่ามีค่าครบตามโหมด

### 7.4 `parse_inputs(raw)`

ลำดับการทำงาน:

1. อ่าน `mode` จาก `raw["mode"]`
   - ไม่มี/ว่าง → `InputError("กรุณาเลือกโหมดไบอัส (divider, fixed, emitter)")`
   - ไม่อยู่ใน `MODES` → `InputError(f"โหมดไบอัสไม่รู้จัก: {mode} (รองรับ: divider, fixed, emitter)")`
2. เอา `MODE_FIELDS[mode]` มาอ่านค่าทีละช่องด้วย `_to_float` (ข้อความไทยเหมือนเดิม)
3. ตรวจความสมเหตุสมผล:
   - ช่องแรงดัน/ตัวต้านทานของโหมดนั้น ≤ 0 → `"{label} ต้องมากกว่า 0"`
   - `beta ≤ 0` → `"β (Beta) ต้องมากกว่า 0"`
   - `vbe < 0` → `"VBE (V) ต้องไม่ติดลบ"`
   - `vbe ≥ vcc` → `"VBE (V) ต้องน้อยกว่า VCC (V)"`
4. คืน `BiasInputs` โดยช่องที่ไม่ใช้เป็น `None`

ข้อความ error เดิมทุกข้อความคงไว้ เพื่อให้ `tests/test_web.py` ที่ assert
`"มากกว่า 0"`, `"ต้องเป็นตัวเลข"`, `"กรุณากรอก"` ยังผ่าน

### 7.5 สมการ

```
Divider : VTH = VCC·R2/(R1+R2) ;  RTH = R1·R2/(R1+R2)      [kΩ]
          IB  = (VTH − VBE) / ((RTH + (β+1)·RE) · 1000)
Fixed   : IB  = (VCC − VBE) / (RB · 1000)
Emitter : IB  = (VCC − VBE) / ((RB + (β+1)·RE) · 1000)

IC  = β·IB
IE  = (β+1)·IB
VE  = IE·RE·1000            (fixed: 0)
VB  = VE + VBE
VC  = VCC − IC·RC·1000
VCE = VC − VE
```

### 7.6 การประกอบผลลัพธ์ (จุดร่วม)

`_assemble(mode, ib, vcc, rc, re, vbe, beta, vth=None, rth=None) -> dict`
คำนวณ IC/IE/VE/VB/VC/VCE, ตัดสิน region, ใส่ warning แล้วคืน dict:

```python
{
    "mode": "divider" | "fixed" | "emitter",
    "ib_ua": float,      # µA
    "ic_ma": float,      # mA
    "ie_ma": float,      # mA
    "vb_v": float,
    "ve_v": float,
    "vc_v": float,
    "vce_v": float,
    "vth_v": float | None,     # divider เท่านั้น
    "rth_kohm": float | None,  # divider เท่านั้น
    "region": "active" | "cutoff" | "saturation",
    "warnings": tuple[str, ...],
}
```

**Region และ warning**

- ถ้า `IB ≤ 0` → `region="cutoff"`, กระแสเป็นศูนย์, `ve=0`, `vc=vcc`,
  `vce=vcc`, warning ว่า Forward-Active ใช้ไม่ได้
  (สำหรับ fixed/emitter กรณีนี้ไม่เกิดเพราะบังคับ `vbe < vcc` แล้ว แต่คงไว้
  เป็น guard ตามใบงานที่ระบุ `IB ≤ 0`)
- **Cutoff: ค่า VB ต่างกันตามโหมด** — divider คง `VB = VTH` (พฤติกรรมเดิมของ
  Lab 02 คือ 0.119 V ในกรณีทดสอบ `r2=1`), fixed/emitter ใช้ `VB = VCC`
  เพราะไม่มีกระแสฐานไหลจึงไม่มีแรงดันตกคร่อม RB
  เหตุผล: anti-goal กำหนดว่าผล Divider ต้องไม่เปลี่ยน และทางกายภาพ VB ใน
  cutoff คือแรงดันที่ขั้วฐานถูกตรึงไว้ ไม่ใช่ `VE + VBE`
- Divider เท่านั้น: `VTH ≤ VBE` → cutoff แบบเดียวกัน (พฤติกรรมเดิมของ Lab 02)
- ถ้า `VCE ≤ VCE_SAT` → `region="saturation"` + warning ว่าแบบจำลองไม่น่าเชื่อถือ
  (ใบงานเขียน `≤` จึงใช้ `<=` ไม่ใช่ `<` เดิม)
- ไม่เข้าเงื่อนไขใด → `region="active"`, `warnings=()`

### 7.7 `app.py`

```python
MODE_FIELDS มาจาก dc_bias           # template ใช้ตัดสินว่าจะซ่อนช่องไหน
DEFAULT_VALUES = {"mode": "divider", "vcc": "12", "r1": "100", "r2": "22",
                  "rb": "1000", "rc": "2.2", "re": "1",
                  "beta": "100", "vbe": "0.7"}
```

- `GET /` → render ด้วย `DEFAULT_VALUES`, `result=None`
- `POST /` → รวม `mode` + **ทุก** ช่องจากฟอร์มเป็น `values` (คงค่าที่พิมพ์ไว้
  แม้ช่องนั้นไม่ใช้ในโหมดปัจจุบัน), เรียก `calculate(mode, parse_inputs(values))`
- **Guard สำหรับโหมดไม่รู้จัก (สำคัญ):** ก่อน render ทุกครั้ง route คำนวณ
  `display_mode = values["mode"] if values["mode"] in MODES else MODE_DIVIDER`
  แล้วส่ง `display_mode` ให้ template ใช้เลือกช่องที่แสดงและเลือก `<option>`
  เหตุผล: ถ้าใช้ `mode_fields[values.mode]` ตรง ๆ กรณี `mode="foo"` หรือไม่ส่ง
  mode จะเกิด `KeyError` → HTTP 500 ซึ่งขัด anti-goal
  (`values["mode"]` ยังคงค่าที่ผู้ใช้ส่งมา เพื่อให้ error message อ้างถึงได้)
- `InputError` → render ใหม่ด้วย `result=None`, `error=str(exc)`, HTTP 400
  (ไม่ค้างผลรอบก่อน)
- สำเร็จ → render ด้วย `result` (dict), HTTP 200

`REGION_LABELS` คงเดิม, `fmt` filter คงเดิม

### 7.8 Template

```
<select name="mode">          3 ตัวเลือก + selected ตาม values.mode
fieldset.grid
  VCC
  RB            class="field {% if 'rb' not in active_fields %}field--unused{% endif %}"
  R1, R2        (divider)
  RC
  RE            (divider, emitter)
  β, VBE
```

- `active_fields = mode_fields[display_mode]` ส่งมาจาก route (ไม่ใช่
  `values.mode` โดยตรง — ดู guard ใน §7.7)
- หัวข้อผลลัพธ์: `2. DC Bias Results — {{ mode_labels[result.mode] }}`
- ตารางแรงดัน/กระแสเหมือนเดิม แต่อ่านจากคีย์ dict
  (`result.vb_v|fmt`, `result.ic_ma|fmt`, `result.ib_ua|fmt`)
- บรรทัดสรุป: divider โชว์ `VTH / RTH`, fixed/emitter ไม่โชว์
- `VCE_SAT` ต้องมาจาก `dc_bias` (ส่งเป็น context) ไม่ hardcode `0.3` ใน HTML
- warning loop คงเดิม (`result.warnings`)
- เปลี่ยน eyebrow/footer เป็น LAB 03 และ sub text ระบุสามโหมด
- error block คงเดิม (result=None ทำให้ไม่มีส่วนผลลัพธ์)

### 7.9 CSS

เพิ่ม

```css
.field--unused { display: none; }
.mode-row { ... }   /* แถว dropdown ให้เต็มความกว้าง grid */
```

ไม่แตะสี/ตัวอักษรเดิม

### 7.10 Tests (แก้แบบ mechanical เท่านั้น)

`tests/test_dc_bias.py`
- `REFERENCE` เพิ่ม `"mode": "divider"`
- `solve()` → `calculate(REFERENCE_mode, parse_inputs(values))` โดยคง override ได้
- assertions เปลี่ยน `.vth` → `["vth_v"]`, `.rth` → `["rth_kohm"]`,
  `.ib` → `["ib_ua"]` (คูณ 1e6 แล้ว), `.ic` → `["ic_ma"]`,
  `.ie` → `["ie_ma"]`, `.vb/.ve/.vc/.vce` → `["vb_v"]` ฯลฯ,
  `.region` → `["region"]`, `.warnings` → `["warnings"]`
- ค่าเลขและ delta เดิมทั้งหมด ห้ามปรับ tolerance ให้ผ่านง่ายขึ้น
- `test_kohm_inputs_are_converted` ยังตรวจ `inputs.r1 == 100.0` และ
  `rth_kohm > 1.0`

`tests/test_web.py`
- `REFERENCE` เพิ่ม `"mode": "divider"`
- ไม่แก้ assertion อื่น

## 8. เอกสารที่จะอัปเดต

| ไฟล์ | สาระ |
|---|---|
| `README.md` | สามโหมด, ตารางช่องอินพุตต่อโหมด, สมการสามชุด, `VCE_SAT = 0.2`, วิธีตรวจผ่านเบราว์เซอร์, ค่าอ้างอิง A1–A5 |
| `docs/validation.md` | เพิ่มหัวข้อ Lab 03: ค่าอ้างอิงอิสระ A1–A5 พร้อม derivation ย่อ, ตารางผลจากเว็บ, test log, หมายเหตุว่า A5 ต้องได้ 400 |
| `docs/design-note.md` | เพิ่มหัวข้อย่อยเรื่องการแยก `_assemble` และการเลือก D1/D2 + แก้เหตุผล `VCE_SAT` เป็น 0.2 V |
| `AGENTS.md` | แก้ `VCE_SAT = 0.3 V` → `0.2 V` (Lab 03) ไม่ให้ governance ขัดกับโค้ด |
| `.gitignore` | เพิ่ม `.playwright-mcp/` (session log ของ MCP) |
| `opencode.json` | ไฟล์ MCP แบบ portable (ไม่มี `environment.PATH`) — commit เป็นหลักฐาน Lab 03 |

## 9. การตรวจรับ (Browser ผ่าน Playwright MCP)

ค่าอ้างอิงอิสระ (คำนวณด้วยมือจากสมการใบงาน, VCC=12 V, RC=2.2 kΩ, β=100,
VBE=0.70 V):

| กรณี | โหมด | อินพุต | IB | IC | VCE |
|---|---|---|---|---|---|
| A1 | divider | R1=100k, R2=22k, RE=1k | 12.2986 µA | 1.2299 mA | 8.0522 V |
| A2 | fixed | RB=1M | 11.3000 µA | 1.1300 mA | 9.5140 V |
| A3 | emitter | RB=1M, RE=1k | 10.2634 µA | 1.0263 mA | 8.7054 V |
| A4 | emitter | RB=1M, RE=2k | 9.4010 µA | 0.9401 mA | 8.0328 V |
| A5 | fixed | RB=0 | — | — | ต้องได้ HTTP 400 + ข้อความเรื่อง RB |

Tolerance ตามใบงาน: IC ±0.01 mA, VCE ±0.02 V

การทำนายก่อนรัน (A4): IC ต้อง **ลด** จาก A3 เพราะ `(β+1)·RE` ใหญ่ขึ้นเป็น
2 เท่า ขณะที่ `RB` คงเดิม → กระแสฐานลด

ตรวจเพิ่ม 1 กรณีด้วยมือ (ไม่ใช้ตารางใบงาน): emitter, RB=470 kΩ, RE=1 kΩ
คำนวณคาดหวัง IB = 11.30/(470+101) mA = 19.79 µA → IC = 1.979 mA,
VCE = 12 − 1.979×2.2 − 2.0 = 5.65 V

## 10. สิ่งที่เหลือให้ผู้ลงมือตัดสิน

- การแบ่ง commit (แนะนำ 3 ก้อน: engine / UI / docs)
- การจัดวาง CSS ของแถว dropdown ให้เข้ากับ grid เดิม
- ถ้อยคำ warning ภาษาไทย (ต้องสื่อว่า Forward-Active ใช้ไม่ได้)
- จะรัน Flask พอร์ตใดระหว่างตรวจ (5000 ตามเดิม)

## 11. ผลการตรวจ design โดย builder (รอบที่ 1)

คำถามที่ builder ยกมาทั้ง 6 ข้อ และข้อสรุป:

| # | เรื่อง | ข้อสรุป |
|---|---|---|
| 1 | ไม่มี test ของ fixed/emitter แต่ `AGENTS.md` บังคับ | **ตัดสินแล้ว: ยึดตามบรีฟ = ไม่เพิ่ม test** คง 27 ตัว, แก้เฉพาะ mechanical (§11.1) |
| 2 | ใครเป็นคนตรวจ A1–A5 | **ผู้ลงมือ (AI) เป็นคนรัน** ผ่าน Playwright MCP: เปิด Flask พอร์ต 5000, กรอกฟอร์มจริง, คัดลอกค่าที่หน้าเว็บแสดงลงตาราง ห้ามใส่ค่าที่ derive เองในคอลัมน์ "ผลจากเว็บ" ถ้ากรณีใดรันไม่ได้ให้เขียน `NOT RUN` + เหตุผล |
| 3 | `mode_fields[values.mode]` → KeyError → 500 | **แก้แล้ว**: `display_mode` guard (§7.7, §7.8) |
| 4 | Cutoff ของ divider: VB = VTH หรือ VBE | **VB = VTH** สำหรับ divider, **VB = VCC** สำหรับ fixed/emitter (§7.6) |
| 5 | `opencode.json` มี path เฉพาะเครื่อง + `.playwright-mcp/` untracked | commit `opencode.json` แบบ **portable ไม่มี `environment.PATH`** (Node อยู่ใน User PATH แล้ว) และเพิ่ม `.playwright-mcp/` ลง `.gitignore`; workaround PATH ใช้เฉพาะระหว่าง session นี้ก่อน restart |
| 6 | `AGENTS.md` และ `docs/design-note.md` ยังเขียน 0.3 V | **แก้เป็น 0.2 V** พร้อมหมายเหตุว่าเปลี่ยนตามใบงาน Lab 03 (ไฟล์ governance ต้องไม่ขัดกับโค้ด) |

### 11.1 คำถามที่ต้องให้ผู้ใช้ตัดสิน — **ตัดสินแล้ว**

ใบงานเขียน "เก็บ tests เดิมไว้ แต่ไม่ต้องสร้าง unittest ใหม่"

**คำตอบของผู้ใช้: ยึดตามบรีฟ (ทาง 2) — ไม่เพิ่ม unittest ใหม่ คงไว้ 27 ตัว**
และให้ทำตามบรีฟให้ตรงที่สุด

ผลที่ตามมา:

- ไม่มี test สำหรับ `fixed_bias`/`emitter_bias`/unknown mode — ตาข่ายกันพลาด
  คือตาราง A1–A5 ที่ตรวจผ่าน Browser เท่านั้น
- เลข "Ran 27 tests" ใน `docs/validation.md` ยังถูกต้อง ไม่ต้องแก้
- `AGENTS.md` ข้อ "ทุกฟีเจอร์ใหม่ต้องมี test" ถือเป็น **ข้อยกเว้นที่ใบงาน Lab 03
  กำหนด** — บันทึกเหตุผลไว้ใน `docs/validation.md` เพื่อไม่ให้ผู้ตรวจคิดว่า
  ลืมเขียน test
- ระหว่างพัฒนา ผมยังใช้ `python -c` / เรียกฟังก์ชันตรง ๆ ตรวจค่าก่อนเปิด
  เบราว์เซอร์ได้ แต่จะไม่เพิ่มไฟล์ test เข้า repo
