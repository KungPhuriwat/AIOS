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
- มี HTTP API server สำหรับ integration testing/automation
- มี Async Job Queue สำหรับงาน benchmark/train แบบ background

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
4. รัน CLI
```powershell
python -m src.ai_os.main
```

## Non-interactive CLI (สำหรับ automation)
```powershell
python -m src.ai_os.main --run "show policy"
python -m src.ai_os.main --run "show dashboard" --run "test provider"
python -m src.ai_os.main --run "ops: echo hello" --approve-ops
python -m src.ai_os.main --run "train python 5"
python -m src.ai_os.main --run "queue train python 5" --run "show jobs"
```

## API Server Mode
รัน server:
```powershell
python -m src.ai_os.main --serve --host 127.0.0.1 --port 8787
```

ตั้ง token (แนะนำ):
```powershell
$env:AIOS_API_TOKEN = "<token>"
```

ตัวอย่างเรียก API:
```powershell
curl http://127.0.0.1:8787/health
curl -H "Authorization: Bearer <token>" http://127.0.0.1:8787/dashboard
curl -X POST http://127.0.0.1:8787/code -H "Content-Type: application/json" -d '{"language":"python","prompt":"write robust parser"}'
curl -X POST http://127.0.0.1:8787/jobs/train -H "Content-Type: application/json" -d '{"language":"python","rounds":5}'
curl http://127.0.0.1:8787/jobs
```

Endpoints:
- `GET /health`
- `GET /dashboard`
- `GET /policy`
- `GET /skills`
- `GET /provider`
- `GET /notify`
- `GET /audit/status`
- `GET /jobs`
- `GET /jobs/{job_id}`
- `POST /code` `{language,prompt}`
- `POST /ops` `{prompt,approved_by_user}`
- `POST /benchmark` `{language}`
- `POST /train` `{language,rounds}`
- `POST /jobs/benchmark` `{language}`
- `POST /jobs/train` `{language,rounds}`
- `POST /provider/test`

## Compile เป็น .exe (Windows)
```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1 -Clean -Smoke
```
ไฟล์ที่ได้:
- `dist/AIOS.exe`

ทดสอบ executable:
```powershell
.\dist\AIOS.exe --run "show policy"
.\dist\AIOS.exe --run "show dashboard"
```

## คำสั่ง CLI
- `code python: เขียนฟังก์ชันหา fibonacci`
- `ops: echo hello`
- `benchmark python`
- `train python 5`
- `queue benchmark python`
- `queue train python 5`
- `show jobs`
- `show job <job_id>`
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
