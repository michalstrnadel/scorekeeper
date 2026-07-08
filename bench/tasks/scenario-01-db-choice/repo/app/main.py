"""Tiny web API — persistence layer to be added."""

from fastapi import FastAPI

app = FastAPI(title="feedly-mini")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
