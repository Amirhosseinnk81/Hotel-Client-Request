from fastapi import FastAPI

app = FastAPI(
    title="Hotel Client Request API",
    description="Backend API for Hotel Client Request Platform",
    version="0.1.0"
)

@app.get("/")
def root():
    return {
        "message": "Hotel Client Request API is running."
    }