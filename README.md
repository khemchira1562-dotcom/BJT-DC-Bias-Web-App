# BJT Bias + CE Amplifier Simulator — ENG29 2121 Lab 03/04

Flask web app ที่ทำสองอย่างแยกชัดเจน:

1. **Lab 03 — Analytical DC Bias** คำนวณ DC Operating Point ด้วยแบบจำลอง
   Forward-Active (β และ VBE คงที่) ได้ 3 โหมด: `divider`, `fixed`, `emitter`
2. **Lab 04 — CE Amplifier Simulator** สร้าง netlist ของวงจร reference เดียว
   แล้วเรียก **ngspice จริง** ผ่าน `subprocess` เพื่อรัน `.op`, `.ac`, `.tran`
   อ่านค่าจาก log ที่ solver คืนมาเท่านั้น ไม่มีค่าสำเร็จที่ฝังไว้ในโค้ด

ผล **Analytical** กับผล **SPICE** แสดงคนละการ์ด มีป้ายกำกับแหล่งที่มาเสมอ
และห้ามนำมารวมกัน

## โหมดไบอัส Lab 03

| โหมด | อุปกรณ์ | ค่าที่ต้องกรอกเพิ่ม |
|---|---|---|
| **Voltage Divider Bias** | R1, R2, RC, RE | – |
| **Fixed Bias** | RB, RC (Emitter ลงกราวด์) | RB |
| **Emitter Bias** | RB, RC, RE | RB, RE |

กด **แสดงช่องของโหมดนี้** หลังสลับ dropdown ทุกครั้ง ปุ่มนี้ render ฟอร์มใหม่
โดยไม่คำนวณ เพื่อกันไม่ให้ค่าที่ซ่อนอยู่ถูกส่งไปโดยผู้ใช้ไม่เห็น

## วงจรอ้างอิง Lab 04

ใช้ VCC / R1 / R2 / RC / RE จากฟอร์ม Lab 03 ร่วมกับส่วนเชื่อม AC:

```
VIN → Cin → Base          R1: VCC→Base      R2: Base→GND
Collector → Cout → Vout → RL → GND
RC: VCC→Collector         RE: Emitter→GND   Q1: NPN
```

ค่าตั้งต้นตามใบงาน: VCC 12 V, R1 100 kΩ, R2 22 kΩ, RC 2.2 kΩ, RE 1 kΩ,
RL 10 kΩ, Cin = Cout = 10 µF, source 10 mV peak @ 1 kHz

| Analysis | คำสั่ง ngspice | ผลที่แสดง |
|---|---|---|
| DC | `.op` | VB, VE, VC, VCE, IC, IE พร้อม model และ engine status |
| AC | `.ac dec 20 fmin fmax` + `.print ac` | กราฟ Bode (gain dB, phase°) + ค่าช่วงความถี่ |
| Transient | `.tran` + `.print tran` | กราฟ Vin/Vout ตามเวลา (mV vs ms) + ทิศทางเฟส |

### ความต้องการก่อนรันจำลอง

- ต้องมี `ngspice` **อยู่ใน PATH** ของ process ที่รัน Flask (ไม่ใช่ pip package)
  ตรวจด้วย `where ngspice` (บน Windows zip build ใช้ `ngspice_con` ซึ่งเป็น
  console build ที่ batch mode รอจนเสร็จได้ — โค้ดเลือกตัวนี้ก่อนเสมอ)
- ติดตั้งแล้วในเครื่องนี้: ngspice 47 ที่
  `C:\Users\B6822019\AppData\Local\ngspice\Spice64\bin` และเพิ่มลง User PATH
- ใส่บรรทัด `.model <ชื่อ> NPN ...` จาก Starter Kit ของอาจารย์ในช่อง **BJT model**
- ค่าตั้งต้น `.model QNPN_LAB04 NPN` เป็นแค่ structural default ของ ngspice
  **ยังไม่ได้ตรวจกับ Starter Kit** และหน้าเว็บจะเตือนทุกครั้งที่ใช้
- ถ้า engine ไม่พร้อม / รันแล้ว error / timeout / log ไม่มีตาราง 결과
  หน้าเว็บจะแสดง HTTP 400 พร้อมข้อความไทย และ **ไม่มีกราฟหรือผลเก่าค้าง**

## โครงสร้าง

```
app.py                  Flask routes: อ่านฟอร์ม → เรียก dc_bias หรือ spice_engine → render
dc_bias.py              Lab 03: validation + สมการ + region (ไม่ import Flask)
spice_engine.py         Lab 04: validate → netlist → subprocess ngspice → parse log
charts.py               แปลง array ที่ parse แล้วเป็น inline SVG (ไม่มี physics)
templates/index.html    ฟอร์ม, ป้าย provenance, ตาราง/กราฟ (Jinja, ไม่มีสมการ)
static/style.css        หน้าตา/responsive (CSS ล้วน ไม่มี JavaScript)
tests/test_dc_bias.py   19 unit tests ของสมการ Lab 03
tests/test_web.py       14 HTTP tests (8 เดิม + 6 สำหรับ Lab 04)
tests/test_spice_engine.py  20 tests ของ adapter (fake runner, ไม่เรียก ngspice)
opencode.json           ตั้งค่า Playwright MCP (ต้องมี Node.js + npx)
docs/validation.md      หลักฐาน A1–A5 และตาราง B1–B8
docs/evidence/          ภาพจากการตรวจ browser จริง
```

## การติดตั้งและรัน

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m flask --app app run --port 5000
```

> ในเครื่องนี้ `python` เป็น Microsoft Store alias ที่ใช้ไม่ได้ ให้ใช้ `py`
> (ใน venv ที่ activate แล้วใช้ `python` ได้ตามปกติ)

เปิด <http://127.0.0.1:5000/> การ double-click `templates/index.html` (file://)
จะไม่มีการคำนวณ เพราะไม่มี Python Backend

## การรัน tests

```powershell
py -m unittest discover -s tests -v
```

**53 tests ผ่านทั้งหมด** (27 เดิม + 26 ใหม่) — 27 เดิมไม่ถูกแตะ
และยังใช้เป็น regression ของ B1

## ข้อมูลออก Lab 03

| ข้อมูลออก | หน่วย | คีย์ |
|---|---|---|
| VB, VE, VC, VCE | V | `vb_v, ve_v, vc_v, vce_v` |
| IB | µA | `ib_ua` |
| IC, IE | mA | `ic_ma, ie_ma` |
| VTH, RTH (divider) | V, kΩ | `vth_v, rth_kohm` |
| Region | – | `active`/`cutoff`/`saturation` |

สมการ: `IB = (VTH−VBE)/((RTH+(β+1)RE)·1000)` (divider),
`IC = β·IB`, `IE = (β+1)·IB`, `VC = VCC−IC·RC·1000`, `VCE = VC−VE`

## ข้อมูลออก Lab 04

| ข้อมูลออก | หน่วย | คีย์ |
|---|---|---|
| Node voltage / current | V, mA | `vb_v, ve_v, vc_v, vce_v, ic_ma, ie_ma` |
| Gain / phase | dB, degree | `gain_db, phase_deg` ใน `series` |
| เวลา / แรงดัน | s, V → แสดงเป็น ms, mV | `time_s, vin_v, vout_v` |
| Engine status | – | `engine`, `engine_status` |
| หลักฐาน | – | `model`, `netlist`, `log_tail` |

IC ในโหมด DC คำนวณจาก `(VCC − VC)/RC` และ IE จาก `VE/RE`
โดยใช้ **node voltage ที่อ่านจาก log จริง** ไม่ได้เอาค่าจาก netlist มาแทน

## Validation และ Warning

อินพุตผิด → HTTP 400 + ข้อความไทย:

- ค่าหาย / ไม่ใช่ตัวเลข / `inf` / `nan`
- R, VCC, β, RL, Cin, Cout ≤ 0, frequency ≤ 0
- `fmax ≤ fmin`, `fmax > 1 GHz`, analysis ไม่รู้จัก
- model ไม่ใช่บรรทัด `.model <ชื่อ> NPN ...` (กัน injection)

แบบจำลองใช้ไม่ได้ → warning (ยังแสดงผล):

- Lab 03: `IB ≤ 0` → Cutoff, `VCE ≤ 0.2 V` → Saturation
- Lab 04 AC: ไม่เจอจุดตัด −3 dB → แสดง `not determined in sweep range`
- Lab 04 transient: ตรวจทิศทางเฟสจาก correlation ของ Vin/Vout
- ใช้ model ตั้งต้น → เตือนว่ายังไม่ validated กับ Starter Kit

## ค่าอ้างอิง A1–A5 (Lab 03)

| กรณี | โหมด | อินพุต | IC | VCE |
|---|---|---|---|---|
| A1 | divider | R1=100k, R2=22k, RE=1k | 1.2299 mA | 8.0522 V |
| A2 | fixed | RB=1 MΩ | 1.1300 mA | 9.5140 V |
| A3 | emitter | RB=1 MΩ, RE=1k | 1.0263 mA | 8.7054 V |
| A4 | emitter | RB=1 MΩ, RE=2k | 0.9401 mA | 8.0328 V |
| A5 | fixed | RB=0 | — | HTTP 400 |

## หลักฐานและสถานะ Lab 04

ดู `docs/validation.md` §12 สำหรับตาราง **B1–B8** แบบ PASS/FAIL/NOT RUN
และ `docs/evidence/` สำหรับภาพจาก browser จริง

สถานะ ณ ที่ตรวจล่าสุด:

- B1–B7 **PASS** ด้วย ngspice จริง + in-app browser ของ OpenCode
  (B2 DC `.op`, B3 เปลี่ยน RE, B4 AC Bode, B5 transient, B6 เปลี่ยน source,
  B7 invalid/engine-fail)
- B8 mobile viewport **NOT RUN** (ตรวจเฉพาะ desktop, tool นี้ปรับ viewport ไม่ได้)
- Playwright MCP **NOT RUN** — ใช้ in-app browser ของ OpenCode แทน
  และบันทึกชื่อ tool ให้ตรงความจริง
- ผล SPICE ยังใช้ structural default model อยู่ ต้องแทนด้วย `.model` จาก Starter Kit
  ก่อนอ้างว่า validated ตามใบงาน

## ข้อจำกัด

- แบบจำลอง Lab 03 ไม่ใช่ SPICE, ใช้ β คงที่, ไม่มี Early effect
- Lab 04 มี **วงจร reference เดียว** ตามใบงาน (ไม่ใช่เครื่องมือออกแบบทั่วไป)
- กราฟถูกสร้างจากผล `.print` จริงเท่านั้น ไม่มีข้อมูล hard-code
- ไม่เพิ่ม dependency นอกเหนือ Flask: SVG ถูก generate จาก array ใน `charts.py`
- ผลทั้งสองชุดไม่ควรใช้ตัดสินใจออกแบบนอกช่วง Forward-Active
