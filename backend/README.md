# CivicFlow Backend

FastAPI monolithic backend service for CivicFlow.

## Running in Development

```bash
# Activate virtual environment
# Windows:
..\venv\Scripts\activate
# Linux/macOS:
source ../venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Health Check
- `GET http://localhost:8000/health` -> `{"status": "ok"}`
- `GET http://localhost:8000/health/db` -> Database connectivity status
