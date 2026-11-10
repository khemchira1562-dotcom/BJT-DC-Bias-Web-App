# Design Note — Lab 02

## ปัญหา

นักศึกษาต้องเห็นความแตกต่างระหว่างหน้า HTML ธรรมดากับ Web Application
ที่มี Backend คำนวณจริง

## แนวทาง

แยกความรับผิดชอบ 3 ชั้น

1. **Presentation** — `templates/index.html` + `static/style.css`
   แสดงฟอร์มและผลลัพธ์ ไม่มีสมการ
2. **Transport** — `app.py` แปลง HTTP form เป็น Python และเลือก template
3. **Engineering** — `dc_bias.py` เป็นโมดูลบริสุทธิ์ที่ทดสอบแยกได้

## การตัดสินใจสำคัญ

| เรื่อง | ทางเลือก | ที่เลือก | เหตุผล |
|---|---|---|---|
| Route | GET/POST `/` เทียบกับ POST `/calculate` | GET/POST `/` | โค้ดน้อย, ตรงสเปก, ไม่ต้อง session |
| Validation | ใน `app.py` เทียบกับใน `dc_bias.py` | ใน `dc_bias.py` | กฎอยู่ที่เดียว ทดสอบตรง |
| หน่วยตัวต้านทาน | Ω เทียบกับ kΩ | kΩ แล้วแปลงใน Backend | ตรงกับค่าตัวอย่างในเอกสาร |
| Test runner | pytest เทียบกับ unittest | unittest | ไม่เพิ่ม dependency |
| เกณฑ์ Saturation | VCE < 0.2 V เทียบกับ < 0.3 V | 0.3 V | เผื่อ margin, ประกาศชัด |

## ผลลัพธ์ที่ต้องการ

ผู้ใช้กรอกค่าอุปกรณ์ กดปุ่มครั้งเดียว เห็น DC Operating Point พร้อมหน่วย
และทราบทันทีเมื่อแบบจำลองใช้ไม่ได้
