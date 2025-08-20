"""Simple test to verify FastAPI works"""

from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Simple Test")

@app.get("/")
def root():
    return {"status": "working", "message": "Simple test backend"}

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    print("🧪 Starting simple test backend...")
    uvicorn.run(app, host="0.0.0.0", port=9001, log_level="info")
