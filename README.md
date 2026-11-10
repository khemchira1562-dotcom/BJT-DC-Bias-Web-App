# BJT DC Bias Web App — ENG29 2121 Lab 02

Flask Web Application สำหรับคำนวณ **DC Operating Point** ของวงจร NPN
Common-Emitter แบบ **Voltage-Divider Bias** ด้วยแบบจำลอง Forward-Active
(β และ VBE คงที่)

หน้าเว็บรับค่าอุปกรณ์ แล้วส่ง HTTP POST ไปให้ Python Backend คำนวณ
ไม่ใช่ตัวเลขที่ฝังไว้ใน HTML

## โครงสร้าง

```
app.py                  Flask routes (GET /, POST /)
dc_bias.py              Validation + สมการวิศวกรรม (ไม่รู้จัก HTML/HTTP)
templates/index.html    ฟอร์มและตารางผลลัพธ์ (Jinja)
static/style.css        หน้าตา/responsive
tests/test_dc_bias.py   Unit tests ของสมการ
tests/test_web.py       HTTP tests ด้วย Flask test client
requirements.txt        Flask
docs/                   Design note, validation, reflection
```

## การติดตั้งและรัน

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m flask --app app run --debug
```

เปิด <http://127.0.0.1:5000/>

> ต้องเปิดผ่าน Flask server เท่านั้น การ double-click `templates/index.html`
> (file://) จะไม่มีการคำนวณ เพราะไม่มี Python Backend

## การรัน tests

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
```

## ค่าเข้า / ค่าแสดงผล

| ข้อมูลเข้า | หน่วย |
|---|---|
| VCC | V |
| R1, R2, RC, RE | **kΩ** (Backend แปลงเป็น Ω) |
| β | - |
| VBE | V |

| ข้อมูลออก | หน่วย |
|---|---|
| VB, VE, VC, VCE | V |
| IC, IE | mA |
| IB | µA |

## สมการ

```
VTH = VCC·R2/(R1+R2)
RTH = R1·R2/(R1+R2)                 [kΩ]
IB  = (VTH − VBE) / ((RTH + (β+1)·RE)·1000)
IC  = β·IB ,  IE = (β+1)·IB
VE  = IE·RE·1000 ,  VB = VE + VBE
VC  = VCC − IC·RC·1000 ,  VCE = VC − VE
```

## Validation และ Warning

- ค่าที่ไม่ใช่ตัวเลข, ค่าที่หายไป, R ≤ 0, β ≤ 0, VCC ≤ 0, VBE < 0,
  VBE ≥ VCC → แสดง error ภาษาไทยและตอบ HTTP 400 (หน้าเว็บไม่ล้ม)
- `VTH ≤ VBE` → Region **Cutoff** พร้อม warning ว่าสมการ Forward-Active ใช้ไม่ได้
  (แสดงกระแสเป็นศูนย์)
- `VCE < VCE_SAT = 0.3 V` → Region **Saturation** พร้อม warning ว่าค่าจาก
  Forward-Active ไม่น่าเชื่อถือ

## ค่าอ้างอิงจากเอกสาร Lab

VCC=12 V, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ, RE=1 kΩ, β=100, VBE=0.70 V

| ปริมาณ | ค่า |
|---|---|
| VTH | 2.164 V |
| RTH | 18.033 kΩ |
| IB | 12.298 µA |
| IC | 1.230 mA |
| IE | 1.242 mA |
| VE | 1.242 V |
| VB | 1.942 V |
| VC | 9.294 V |
| VCE | 8.052 V |
| Region | Active |

## ข้อจำกัด

แบบจำลองนี้ไม่ใช่ SPICE/ngspice, ใช้ β คงที่, ไม่มี Early effect,
ไม่ครอบคลุม AC/Transient และไม่ควรใช้ตัดสินใจออกแบบจริงนอกช่วง Forward-Active
