# AGENTS.md — Conventions for this repository

## ภาษาและสไตล์

- UI copy เป็นภาษาไทย; ชื่อตัวแปร/ฟังก์ชัน/หน่วยเป็นภาษาอังกฤษ
- Python ต้องผ่าน `python -m unittest discover -s tests -v`
- ใช้ type hints และ `from __future__ import annotations`
- ไม่เพิ่ม dependency นอกจาก Flask เว้นแต่ตกลงกันก่อน

## ขอบเขตความรับผิดชอบ

- `dc_bias.py`: parsing, validation, สมการ, region detection — **ห้าม import Flask**
- `app.py`: อ่านฟอร์ม, เรียก `dc_bias`, render template — **ห้ามคำนวณเอง**
- `templates/`: แสดงผลเท่านั้น — **ห้ามมีสมการฟิสิกส์**
- `static/`: CSS เท่านั้น ไม่มี JavaScript framework
- `tests/`: ทุกฟีเจอร์ใหม่ต้องมี test ก่อน/พร้อมโค้ด

## กติกาทางวิศวกรรม

- ค่าตัวต้านทานรับเป็น kΩ แล้วคูณ 1000 ใน `dc_bias.py`
- `VCE_SAT = 0.3 V` เป็นค่าคงที่ที่ประกาศใน `dc_bias.py`
- ค่าที่ผิดต้อง raise `InputError` ข้อความภาษาไทย ไม่ปล่อยเป็น HTTP 500
- เมื่อออกนอก Forward-Active ต้องมี warning เสมอ

## Git

- Commit ผ่าน GitHub Desktop
- ข้อความ commit ภาษาอังกฤษ รูปแบบ `type: summary`
- ห้าม commit `.venv/`, `__pycache__/`, `.env`, credentials
