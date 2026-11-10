# Validation — Lab 02

## 1. การคำนวณอ้างอิงด้วยมือ

ค่าทดลอง: VCC = 12 V, R1 = 100 kΩ, R2 = 22 kΩ, RC = 2.2 kΩ, RE = 1 kΩ,
β = 100, VBE = 0.70 V

```
VTH = 12 × 22 / (100 + 22)      = 2.1639 V
RTH = 100 × 22 / (100 + 22)     = 18.0328 kΩ
IB  = (2.1639 − 0.70) / (18.0328k + 101 × 1k)
    = 1.4639 / 119032.8         = 12.298 µA
IC  = 100 × 12.298 µA           = 1.2298 mA
IE  = 101 × 12.298 µA           = 1.2421 mA
VE  = 1.2421 mA × 1 kΩ          = 1.2421 V
VB  = 1.2421 + 0.70             = 1.9421 V
VC  = 12 − 1.2298 mA × 2.2 kΩ  = 9.2943 V
VCE = 9.2943 − 1.2421           = 8.0522 V
```

ตรวจสอบย้อนกลับ: VB − VE = 1.9421 − 1.2421 = 0.7000 V = VBE ✓
และ VCE = 8.052 V > 0.3 V → Active ✓

## 2. ผลจาก Web App

| ปริมาณ | ค่าจากมือ | ค่าจากเว็บ | ต่าง |
|---|---|---|---|
| VTH | 2.164 V | 2.164 V | 0 |
| RTH | 18.033 kΩ | 18.033 kΩ | 0 |
| IB | 12.298 µA | 12.298 µA | 0 |
| IC | 1.230 mA | 1.230 mA | 0 |
| IE | 1.242 mA | 1.242 mA | 0 |
| VE | 1.242 V | 1.242 V | 0 |
| VB | 1.942 V | 1.942 V | 0 |
| VC | 9.294 V | 9.294 V | 0 |
| VCE | 8.052 V | 8.052 V | 0 |

> ค่าจากเว็บยืนยันด้วย `Invoke-WebRequest` (POST) เมื่อ 2026-11-10:
> VB = 1.942 V, VCE = 8.052 V, Region = Active

## 3. กรณีทดสอบเพิ่มเติม

| กรณี | อินพุต | ผลที่คาดหวัง |
|---|---|---|
| Cutoff | R2 = 1 kΩ (VTH ≈ 0.119 V) | Region Cutoff, IC = 0, warning |
| Saturation | RC = 10 kΩ | VCE ติดลบ, Region Saturation, warning |
| R ผิด | R1 = 0 | HTTP 400 + "ต้องมากกว่า 0" |
| ไม่ใช่ตัวเลข | VBE = "abc" | HTTP 400 + "ต้องเป็นตัวเลข" |
| ข้อมูลหาย | ไม่กรอก β | HTTP 400 + "กรุณากรอก" |

## 4. Test Log

```
python -m unittest discover -s tests -v

Ran 27 tests in 0.030s

OK
```

- `tests/test_dc_bias.py`: 19 tests — ค่าอ้างอิง 8, region 2, validation 9
- `tests/test_web.py`: 8 tests — GET form, POST ผลลัพธ์, backend-not-hardcoded,
  invalid 400, non-numeric 400, missing 400, cutoff warning, saturation warning
