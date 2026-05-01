# Backend - 自助报表系统

## Setup

```bash
cp .env.example .env
# Edit .env with your MySQL credentials and DashScope API key

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## API Docs

Visit http://localhost:8000/docs for Swagger UI.
