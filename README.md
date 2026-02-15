# AI OS Layer MVP (Windows-first)

MVP นี้เป็นชั้น AI ครอบ OS แบบ "ควบคุมได้ ตรวจสอบได้" โดยเน้น:
- คุยภาษาไทยได้
- จัดการงาน coding หลายภาษา
- มีระบบ permission gate แบบ policy + command parser
- มี denylist/allowlist ตาม platform สำหรับงานระบบ
- มี system executor ที่รันคำสั่งจริงแบบควบคุมสิทธิ์ได้
- มี skill registry + benchmark engine + แจ้งเตือนเมื่อความสามารถเพิ่มขึ้น
- มี honesty report (รู้จริง vs คาดเดา + confidence)
- รองรับ LLM provider จริง (OpenAI/Ollama/Opencode)
- แจ้งเตือนออกนอกเครื่อง (LINE/Discord/Email)
- มี signed audit log แบบ HMAC chain (tamper-evident)

## เริ่มใช้งานเร็ว
1. คัดลอกไฟล์ตัวอย่าง
```powershell
Copy-Item .env.example .env
```
2. ตั้งค่า `.env`
- `AIOS_LLM_PROVIDER=fallback|openai|ollama|opencode`
- `AIOS_OPS_MODE=read|admin`
- `AIOS_ENABLE_OPS_EXEC=1` เพื่อรันคำสั่ง ops จริง
3. (แนะนำ) ตั้ง secret สำหรับ signed audit
```powershell
$env:AIOS_AUDIT_SECRET = "<strong_random_secret>"
```
4. รัน
```powershell
python -m src.ai_os.main
```

## คำสั่ง CLI
- `code python: เขียนฟังก์ชันหา fibonacci`
- `ops: echo hello`
- `benchmark python`
- `show dashboard`
- `show policy`
- `show skills`
- `show audit`
- `show audit status`
- `show provider`
- `show notify status`
- `test provider`
- `exit`

## ทดสอบครบชุดแบบคำสั่งเดียว
```powershell
python scripts/checklist_10min.py
```

## Pre-commit Security Gates
ตั้งค่าหนึ่งครั้ง:
```powershell
python -m pip install pre-commit
python -m pre_commit install
```

รันตรวจเองทุกไฟล์:
```powershell
python -m pre_commit run --all-files
```

## CI
- มี GitHub Actions ที่ `.github/workflows/ci.yml`
- CI บังคับรัน `pre-commit run --all-files` และ `python -m pytest -q` ทุก push/PR

## Requirement Acceptance Test
รันชุดทดสอบตาม requirement หลัก (ไทย, หลายภาษา, self-learning, notification, honesty, security, audit, dashboard):
```powershell
python scripts/acceptance_requirements.py
```
