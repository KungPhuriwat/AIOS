# AI OS Layer MVP (Windows-first)

MVP นี้เป็นชั้น AI ครอบ OS แบบ "ควบคุมได้ ตรวจสอบได้" โดยเน้น:
- คุยภาษาไทยได้
- จัดการงาน coding หลายภาษา
- มีระบบ permission gate แบบ policy + command parser
- มี denylist/allowlist ตาม platform สำหรับงานระบบ
- มี skill registry + แจ้งเตือนเมื่อความสามารถเพิ่มขึ้น
- มี honesty report (รู้จริง vs คาดเดา + confidence)
- รองรับ LLM provider จริง (OpenAI/Ollama/Opencode)
- แจ้งเตือนออกนอกเครื่อง (LINE/Discord/Email)
- มี signed audit log แบบ HMAC chain (tamper-evident)

## โครงสร้าง
- `src/ai_os/core/orchestrator.py` แกนประสานงานหลัก
- `src/ai_os/core/permissions.py` policy + parser + allowlist/denylist
- `src/ai_os/core/audit.py` signed audit logger + chain verify
- `src/ai_os/core/skill_registry.py` เก็บระดับความสามารถ
- `src/ai_os/core/learner.py` อัปเกรดความสามารถจากผลลัพธ์จริง
- `src/ai_os/core/honesty.py` รายงานความมั่นใจอย่างโปร่งใส
- `src/ai_os/core/notifier.py` แจ้งเตือน + fan-out + retry/backoff
- `src/ai_os/core/retry.py` ยูทิล retry/backoff กลาง
- `src/ai_os/core/env_loader.py` โหลดค่า `.env`
- `src/ai_os/agents/coding_agent.py` provider router และ coding agent
- `src/ai_os/main.py` CLI สำหรับใช้งาน
- `scripts/checklist_10min.py` สคริปต์ทดสอบครบชุดแบบคำสั่งเดียว

## เริ่มใช้งานเร็ว
1. คัดลอกไฟล์ตัวอย่าง
```powershell
Copy-Item .env.example .env
```
2. ใส่ค่า key/token ที่ต้องใช้ใน `.env`
3. (แนะนำ) ตั้ง secret สำหรับ signed audit
```powershell
$env:AIOS_AUDIT_SECRET = "<strong_random_secret>"
```
4. รัน
```powershell
python -m src.ai_os.main
```

## ตั้งค่า LLM Provider (ผ่าน `.env`)
- `AIOS_LLM_PROVIDER=fallback|openai|ollama|opencode`
- ตั้ง retry กลาง: `AIOS_RETRY_ATTEMPTS=3`

### OpenAI
- `OPENAI_API_KEY`
- `OPENAI_MODEL` (default: `gpt-4.1-mini`)
- `OPENAI_BASE_URL` (default: `https://api.openai.com/v1/responses`)

### Opencode
- `OPENCODE_API_KEY`
- `OPENCODE_MODEL` (default: `opencode/coder`)
- `OPENCODE_ENDPOINT` (default: `https://api.opencode.ai/v1/chat/completions`)

### Ollama
- `OLLAMA_MODEL` (default: `qwen2.5-coder:7b`)
- `OLLAMA_ENDPOINT` (default: `http://127.0.0.1:11434/api/generate`)

## ตั้งค่าการแจ้งเตือนออกนอกเครื่อง
### Discord
- `AIOS_DISCORD_WEBHOOK`

### LINE (Messaging API Push)
- `AIOS_LINE_CHANNEL_ACCESS_TOKEN`
- `AIOS_LINE_TO`

### Email (SMTP)
- `AIOS_EMAIL_SMTP_HOST`
- `AIOS_EMAIL_SMTP_PORT`
- `AIOS_EMAIL_USERNAME`
- `AIOS_EMAIL_PASSWORD`
- `AIOS_EMAIL_TO`

## คำสั่ง CLI
- `code python: เขียนฟังก์ชันหา fibonacci`
- `ops: del /f /q C:\important\*`
- `show skills`
- `show audit`
- `show audit status` (ตรวจความถูกต้องของ signed chain)
- `show provider`
- `show notify status`
- `test provider` (ยิงทดสอบ provider ปัจจุบันและรายงาน latency)
- `exit`

## Security Hardening
- parser แยก command ตาม `|`, `;`, `&&`, `||`
- denylist ต่อ platform + signature detection (`rm -rf`, `del /f /q`, `erase`, `drop database`, obfuscation)
- allowlist ในโหมด `admin` สำหรับคำสั่ง ops ที่ไม่อนุมัติ
- signed audit log ด้วย `HMAC-SHA256` chain
- ไฟล์ audit เก่ารูปแบบเดิมจะถูก backup และ migrate อัตโนมัติ
- ตรวจ chain integrity ผ่าน `show audit status`

## 10-Minute Checklist (คำสั่งเดียว)
รัน:
```powershell
python scripts/checklist_10min.py
```

สิ่งที่สคริปต์ตรวจให้:
- `pytest` ทั้งหมด
- `pre-commit` ทั้งหมด
- provider/notify/audit health
- security bypass regression (`rm`, `del`, `erase obfuscation`)

## Pre-commit Security Gates
ตั้งค่าหนึ่งครั้ง:
```powershell
python -m pip install pre-commit
python -m pre_commit install
```

สิ่งที่จะรันก่อน commit:
- `ruff` + `ruff-format`
- `pytest security hardening tests`
- `pytest full suite`

รันตรวจเองทุกไฟล์:
```powershell
python -m pre_commit run --all-files
```

## CI
- มี GitHub Actions ที่ `.github/workflows/ci.yml`
- CI บังคับรัน `pre-commit run --all-files` และ `python -m pytest -q` ทุก push/PR

## ทดสอบ
```powershell
python -m pytest -q
```
