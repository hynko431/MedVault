cd AI_OCR_Service

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

then we got the FastAPI doc where we can test the S3 image url.
