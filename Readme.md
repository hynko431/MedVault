1️⃣ Start server
python -m uvicorn app.main:app --reload

2️⃣ Test health

Open browser:

http://127.0.0.1:8000/health

Expected:

{
  "status": "ok",
  "service": "ai-ocr-search"
}

3️⃣ Open Swagger
http://127.0.0.1:8000/doc
