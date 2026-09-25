from fastapi import FastAPI

app = FastAPI(title="ChangeLens API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Return a lightweight readiness response."""
    return {"status": "ok", "service": "changelens-backend"}


# Future API boundary:
# POST /analyze will be introduced once the analyzer workflow is implemented.
