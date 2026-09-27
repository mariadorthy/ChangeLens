from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router as api_router

app = FastAPI(title="ChangeLens API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(api_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a lightweight readiness response."""
    return {"status": "ok", "service": "changelens-backend"}