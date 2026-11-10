# BJT DC Bias Web App — Design

**วันที่:** 2026-11-10
**รายวิชา:** ENG29 2121 — Lab 02
**สถานะ:** อนุมัติโดยนักศึกษา (แนวทาง + การกรอกค่า kΩ) เมื่อ 2026-11-10

## Intent และเหตุผล

สร้าง Flask Web Application หลายไฟล์สำหรับคำนวณ DC Operating Point ของวงจร
NPN Common-Emitter แบบ Voltage-Divider Bias เพื่อให้เห็นความแตกต่างระหว่าง
Frontend (Browser/Template) กับ Backend (Python) จริง ไม่ใช่ HTML ที่ฝังตัวเลขไว้
และใช้เป็นจุดเริ่มต้นของ Virtual Transistor Laboratory ในสัปดาห์ถัดไป

## Goals

- เปิดผ่าน `http://127.0.0.1:5000/` ได้จริงด้วย Flask development server
- รับ `VCC`, `R1`, `R2`, `RC`, `RE` (kΩ), `β`, `VBE` (V)
- คำนวณ `VB`, `VE`, `VC`, `VCE`, `IC` พร้อมหน่วย และแสดง `IB`, `IE` เพิ่ม
- Validation: missing / non-numeric / R≤0 / β≤0 / VCC≤0 / VBE ผิดช่วง
- Warning เมื่ออยู่นอก Forward-Active (Cutoff / Saturation)
- Automated tests: engineering math + Flask HTTP

## Non-goals

- AC small-signal, Bode plot, transient, signal generator
- SPICE/ngspice, DC load line
- Bias topology อื่น (Fixed, Emitter bias)
- JavaScript framework, authentication, database

## Constraints

- Python 3.13, Flask 3.x เท่านั้น (ไม่เพิ่ม dependency อื่น)
- `dc_bias.py` ต้องไม่ import Flask/HTML/HTTP
- Template ต้องไม่มีสมการฟิสิกส์
- ค่าตัวต้านทานกรอกเป็น **kΩ** แล้วแปลงเป็น Ω ใน Backend
- `VCE_SAT = 0.3 V` เป็นค่าคงที่ที่ประกาศชัดเจน
- Commit/Push ผ่าน GitHub Desktop (ไม่ใช้ git CLI)

## Approaches ที่พิจารณา

| ประเด็น | ทางเลือก | ที่เลือก | เหตุผล |
|---|---|---|---|
| Route | (a) GET/POST `/` หน้าเดียว<br>(b) POST `/calculate`<br>(c) PRG + flash | **(a)** | โค้ดน้อยสุด ตรงสเปก A1/A2 ไม่ต้องใช้ session |
| Validation | (a) ใน `dc_bias.py` raise `InputError`<br>(b) ใน `app.py` | **(a)** | กฎอยู่ที่เดียว เทสต์ได้ตรง ไม่กระจาย |
| Tests | (a) `unittest`<br>(b) `pytest` | **(a)** | ไม่เพิ่ม dependency ตรงคำสั่งในเอกสาร |
| Region | (a) Cutoff `VTH ≤ VBE`, Saturation `VCE < 0.3 V`<br>(b) `VCE ≤ 0.2 V` | **(a)** | เผื่อ margin ของ BC junction และประกาศค่าชัดเจน |

## Design

### โครงไฟล์

```
app.py                  Flask routes + Jinja filter
dc_bias.py              parsing, validation, สมการ, region detection
templates/index.html    ฟอร์ม + ผลลัพธ์
static/style.css        responsive layout
tests/test_dc_bias.py   engineering unit tests
tests/test_web.py       Flask test client
requirements.txt        Flask
README.md               วิธีติดตั้ง/รัน/สมมติฐาน
AGENTS.md               conventions สำหรับ AI
docs/                   design note, validation, reflection
```

### Interface หลัก

```python
VCE_SAT = 0.3
FIELD_NAMES = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")

class InputError(ValueError): ...

@dataclass(frozen=True)
class BiasInputs:   # vcc V, r1..re kΩ, beta, vbe V
@dataclass(frozen=True)
class BiasResult:   # vth, rth(kΩ), ib/ic/ie(A), vb/ve/vc/vce(V), region, warnings

def parse_inputs(raw: Mapping[str, str]) -> BiasInputs
def calculate(inputs: BiasInputs) -> BiasResult
```

### สมการ (Forward-Active)

```
VTH = VCC·R2/(R1+R2)
RTH = R1·R2/(R1+R2)                 [kΩ]
IB  = (VTH − VBE) / ((RTH + (β+1)·RE)·1000)
IC  = β·IB ,  IE = (β+1)·IB
VE  = IE·RE·1000 ,  VB = VE + VBE
VC  = VCC − IC·RC·1000 ,  VCE = VC − VE
```

### Region detection

- **Cutoff:** `VTH ≤ VBE` → IB = IC = IE = 0, VE = 0, VB = VTH, VC = VCC,
  VCE = VCC, `region="cutoff"`, warning ว่าใช้ Forward-Active ไม่ได้
- **Saturation:** `VCE < VCE_SAT` → รายงานค่าตาม active model พร้อม warning
  ว่าค่าที่ได้ไม่น่าเชื่อถือ (ไม่ clamp ค่า)
- **Active:** กรณีอื่น

### Error handling

`parse_inputs` โยน `InputError` ข้อความภาษาไทยข้อความเดียว (จุดแรกที่ผิด)
`app.py` จับแล้ว render หน้าเดิมด้วย HTTP 400 พร้อมคงค่าที่ผู้ใช้กรอกไว้

### Testing strategy

- `test_dc_bias.py`: ค่าอ้างอิงจากตัวอย่างในเอกสาร, การแปลง kΩ, cutoff,
  saturation, input ผิดทุกแบบ
- `test_web.py`: GET 200 + ฟอร์ม, POST ค่าถูกต้องเห็นผล, POST ค่าผิดได้ 400
  และข้อความ error, เปลี่ยน VCC แล้วผลเปลี่ยน (พิสูจน์ว่าไม่ได้ hardcode)

## What's left to the builder

- รายละเอียดหน้าตา/สี (ยึดโทน navy–teal ตาม handout)
- ข้อความ warning/error ที่อ่านง่าย
- การแบ่ง commit ผ่าน GitHub Desktop
