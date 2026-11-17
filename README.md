# BJT DC Bias Web App — ENG29 2121 Lab 03

Flask Web Application สำหรับคำนวณ **DC Operating Point** ของวงจร NPN
Common-Emitter ด้วยแบบจำลอง Forward-Active (β และ VBE คงที่) เลือกได้สามโหมด

| โหมด | อุปกรณ์ | ค่าที่ต้องกรอกเพิ่ม |
|---|---|---|
| **Voltage Divider Bias** | R1, R2, RC, RE | – (โหมดเดิมของ Lab 02) |
| **Fixed Bias** | RB, RC (Emitter ลงกราวด์) | RB |
| **Emitter Bias** | RB, RC, RE | RB, RE |

หน้าเว็บรับค่าอุปกรณ์ แล้วส่ง HTTP POST ไปให้ Python Backend คำนวณ
ไม่ใช่ตัวเลขที่ฝังไว้ใน HTML — เลือก Divider ด้วยค่าเดิมของ Lab 02 แล้วผล
ต้องเท่าเดิมเป๊ะ (IC 1.2299 mA, VCE 8.0522 V)

### ขั้นตอนใช้งาน

1. เลือกโหมดจาก dropdown **โหมดไบอัส**
2. กด **แสดงช่องของโหมดนี้** เพื่อให้ฟอร์มแสดงเฉพาะช่องที่โหมดนั้นต้องใช้
3. กรอกค่า แล้วกด **Calculate DC Bias**

> ต้องกดปุ่มที่ 2 ก่อนคำนวณเมื่อเพิ่งสลับโหมด เพราะช่องที่ซ่อนอยู่ (เช่น RB ตอน
> อยู่โหมด Divider) ยังถูกส่งไปกับฟอร์ม ถ้ากด Calculate ทันทีจะได้ผลที่คำนวณจาก
> ค่าที่ผู้ใช้ยังไม่เห็น — ปุ่มนี้จึงมีไว้กันความเข้าใจผิดนั้น

## โครงสร้าง

```
app.py                  Flask routes (GET /, POST /) + เลือกโหมดที่แสดง
dc_bias.py              Validation + สมการวิศวกรรม (ไม่รู้จัก HTML/HTTP)
templates/index.html    ฟอร์ม, dropdown โหมด, ตารางผลลัพธ์ (Jinja)
static/style.css        หน้าตา/responsive (CSS ล้วน ไม่มี JavaScript)
tests/test_dc_bias.py   Unit tests ของสมการ
tests/test_web.py       HTTP tests ด้วย Flask test client
opencode.json           ตั้งค่า MCP server (Playwright) สำหรับตรวจผ่าน Browser
docs/                   Design note, validation, reflection, evidence/
```

## การติดตั้งและรัน

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m flask --app app run --port 5000
```

เปิด <http://127.0.0.1:5000/>

> ต้องเปิดผ่าน Flask server เท่านั้น การ double-click `templates/index.html`
> (file://) จะไม่มีการคำนวณ เพราะไม่มี Python Backend

## การรัน tests

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
```

27 tests (19 unit + 8 HTTP) — ตามใบงาน Lab 03 ไม่ได้เพิ่ม unittest ใหม่
สำหรับสองโหมดใหม่ แต่ปรับวิธีอ่านผลให้ตรงกับ `dict` ที่คืนจาก `calculate()`
การตรวจรับของโหมดใหม่ทำผ่าน Browser (ดูหัวข้อถัดไป)

## ช่องอินพุตต่อโหมด

| ช่อง | divider | fixed | emitter |
|---|---|---|---|
| VCC (V) | ✓ | ✓ | ✓ |
| R1, R2 (kΩ) | ✓ | – | – |
| RB (kΩ) | – | ✓ | ✓ |
| RC (kΩ) | ✓ | ✓ | ✓ |
| RE (kΩ) | ✓ | – | ✓ |
| β | ✓ | ✓ | ✓ |
| VBE (V) | ✓ | ✓ | ✓ |

ช่องที่ไม่ใช้จะถูกซ่อนด้วย CSS (`field--unused`) แต่ยังถูกส่งไปกับฟอร์ม
`parse_inputs()` อ่านเฉพาะช่องของโหมดนั้น ค่าขยะในช่องอื่นจึงไม่ทำให้ error

## ข้อมูลออก

| ข้อมูลออก | หน่วย | คีย์ใน `dict` |
|---|---|---|
| VB, VE, VC, VCE | V | `vb_v, ve_v, vc_v, vce_v` |
| IB | µA | `ib_ua` |
| IC, IE | mA | `ic_ma, ie_ma` |
| VTH, RTH (divider) | V, kΩ | `vth_v, rth_kohm` |
| Region | – | `region` (`active`/`cutoff`/`saturation`) |
| คำเตือน | – | `warnings` |

## สมการ

```
Divider : VTH = VCC·R2/(R1+R2) ,  RTH = R1·R2/(R1+R2)      [kΩ]
          IB  = (VTH − VBE) / ((RTH + (β+1)·RE) · 1000)
Fixed   : IB  = (VCC − VBE) / (RB · 1000)
Emitter : IB  = (VCC − VBE) / ((RB + (β+1)·RE) · 1000)

ใช้ร่วมกันทุกโหมด
IC  = β·IB ,  IE = (β+1)·IB
VE  = IE·RE·1000            (Fixed: RE = 0 → VE = 0)
VB  = VE + VBE
VC  = VCC − IC·RC·1000
VCE = VC − VE
```

## Validation และ Warning

**อินพุตผิด → HTTP 400 + ข้อความไทย (หน้าเว็บไม่ล้ม)**

- ค่าหายไป, ไม่ใช่ตัวเลข, เป็น `inf`/`nan`
- ตัวต้านทานหรือ VCC ≤ 0, β ≤ 0, VBE < 0, VBE ≥ VCC
- ไม่ส่ง `mode` มา หรือส่งค่าที่ไม่รู้จัก → error (ไม่เดาเป็น Divider)

**แบบจำลองใช้ไม่ได้ → warning (ยังแสดงผล)**

- `IB ≤ 0` → Region **Cutoff** (แสดงกระแสเป็นศูนย์)
- `VCE ≤ VCE_SAT = 0.2 V` → Region **Saturation** + เตือนว่า
  Forward-Active Approximation ไม่น่าเชื่อถือ

## ค่าอ้างอิง A1–A5 (VCC = 12 V, RC = 2.2 kΩ, β = 100, VBE = 0.70 V)

| กรณี | โหมด | อินพุต | IC | VCE |
|---|---|---|---|---|
| A1 | divider | R1=100k, R2=22k, RE=1k | 1.2299 mA | 8.0522 V |
| A2 | fixed | RB=1 MΩ | 1.1300 mA | 9.5140 V |
| A3 | emitter | RB=1 MΩ, RE=1 kΩ | 1.0263 mA | 8.7054 V |
| A4 | emitter | RB=1 MΩ, RE=2 kΩ | 0.9401 mA | 8.0328 V |
| A5 | fixed | RB=0 | — | HTTP 400 |

ภาพหน้าจอจากการตรวจผ่าน Playwright MCP อยู่ที่ `docs/evidence/`
รายละเอียดการคำนวณมือและค่าที่อ่านได้จริงอยู่ที่ `docs/validation.md`

## การตรวจผ่าน Browser ด้วย Playwright MCP

`opencode.json` ตั้ง MCP server ไว้ให้แล้ว (ต้องมี Node.js และ `npx` ใน PATH)

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

ตรวจสถานะด้วย `opencode mcp list` ต้องขึ้น `✓ playwright connected`
แล้วสั่ง agent ให้เปิด <http://127.0.0.1:5000/> กรอกค่า และอ่านผลจากหน้าเว็บ

> `@playwright/mcp@latest` ไม่ได้ pin เวอร์ชัน — เปิดใช้เฉพาะเมื่อต้องการตรวจซ้ำ
> เพราะ `npx -y` จะดาวน์โหลดแพ็กเกจทุกครั้งที่เริ่ม server และต้องมี Node.js
> อยู่ใน `PATH` ของ process ที่รัน OpenCode

## ข้อจำกัด

แบบจำลองนี้ไม่ใช่ SPICE/ngspice, ใช้ β คงที่, ไม่มี Early effect,
ไม่มี DC Load Line / AC / Transient / bypass capacitor และไม่ควรใช้
ตัดสินใจออกแบบจริงนอกช่วง Forward-Active
