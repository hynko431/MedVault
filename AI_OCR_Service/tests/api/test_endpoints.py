import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

start_time = time.time()
from fastapi.testclient import TestClient
from app.main import app
print(f"App loaded in {time.time() - start_time:.2f}s")
client = TestClient(app)
resp = client.get("/health")
print(f"Health Status: {resp.status_code}")
print(f"Health JSON: {resp.json()}")

# Test the chat endpoint without loading standard models yet to see if RAG loads lazily
chat_resp = client.post("/api/v1/chat/medicine-chat", json={"question": "What is aspirin?", "chat_history": []})
print(f"Chat Response Status: {chat_resp.status_code}")
