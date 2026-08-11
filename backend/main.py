from fastapi import FastAPI

app = FastAPI(
    title="OMNI API",
    description="Operational Multi-agent Network Intelligence",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "system": "OMNI",
        "message": "OMNI backend is running!",
        "status": "online"
    }