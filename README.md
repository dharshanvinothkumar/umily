# Umily

**Voice-first, permission-controlled AI computer agent for Windows.**

Umily lets you control authorized websites, applications, files, and development tools through natural-language commands — via text or voice.

---

## Features (Phase 1 — Foundation)

- **FastAPI backend** with structured routing and middleware
- **SQLite database** with SQLAlchemy ORM (tasks, permissions, settings)
- **Control Center** — premium dark-theme frontend dashboard
- **Command endpoint** — submit natural-language commands via text
- **Task history** — persistent task recording
- **Permission CRUD** — configure granular access rules
- **System status** — health monitoring endpoint
- **Structured logging** — loguru with console + rotating file output

## Architecture

```
              USER
               │
       ┌───────┴───────┐
       │               │
   VOICE INPUT     TEXT INPUT
       │               │
       └───────┬───────┘
               ▼
        FASTAPI BACKEND
               │
               ▼
          UMILY AGENT
               │
               ▼
          GEMINI API
               │
               ▼
         TASK PLANNER
               │
               ▼
       PERMISSION MANAGER
               │
               ▼
         TOOL EXECUTOR
```

## Tech Stack

| Layer       | Technology               |
|-------------|--------------------------|
| Backend     | Python, FastAPI, Uvicorn |
| Database    | SQLite, SQLAlchemy       |
| AI          | Gemini API (Phase 2+)    |
| Browser     | Playwright (Phase 5+)    |
| Windows     | pywinauto (Phase 9+)     |
| Voice       | faster-whisper (Phase 12+)|
| TTS         | edge-tts (Phase 14+)     |
| Frontend    | HTML, CSS, JavaScript    |

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd umily

# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment template
copy .env.example .env
# Edit .env with your settings
```

## Environment Setup

Edit `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

## Running

```bash
# Start the server
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open [http://localhost:8000](http://localhost:8000) to access the Control Center.

## API Endpoints

| Method | Path             | Description              |
|--------|------------------|--------------------------|
| POST   | /api/command     | Submit a text command    |
| POST   | /api/voice       | Voice input (Phase 12+)  |
| GET    | /api/tasks       | List recent tasks        |
| GET    | /api/tasks/{id}  | Get task details         |
| POST   | /api/confirm     | Confirm a pending action |
| POST   | /api/cancel      | Cancel a task            |
| GET    | /api/permissions | List permissions         |
| POST   | /api/permissions | Set a permission         |
| GET    | /api/status      | System health            |

## Testing

```bash
pytest tests/ -v
```

## Security

- API keys stored in `.env` only — never in frontend code
- Permission system enforces granular access control
- Gemini never has direct computer access
- All actions are logged
- Consequential actions require user confirmation

## Current Limitations

- Phase 1: No Gemini integration (echo mode only)
- Phase 1: No agent/planner logic
- Phase 1: No browser or Windows automation
- Phase 1: No voice input/output

## Roadmap

1. ✅ **Phase 1** — Foundation (FastAPI, DB, frontend)
2. ✅ **Phase 2** — Gemini API integration
3. ✅ **Phase 3** — Agent planner & tool executor
4. ✅ **Phase 4** — Permission enforcement (ALLOW, ASK, BLOCK)
5. ✅ **Phase 5** — Browser automation (Playwright tool system)
6. ✅ **Phase 6–8** — LeetCode agent, adaptive error recovery, confirmation loop
7. ✅ **Phase 9–11** — Windows automation, filesystem tools, desktop system commands
8. ⬜ **Phase 12–14** — Voice pipeline (STT, wake word, TTS)
9. ⬜ **Phase 15–16** — Background mode, system tray
10. ⬜ **Phase 17** — Polish and testing

---

*Umily — Gemini thinks. The Agent plans. The Permission Manager controls. You stay in control.*
