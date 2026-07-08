"""Users endpoints. NOTE: serializer code needs cleanup."""

from fastapi import FastAPI, HTTPException

app = FastAPI(title="partner-api")

_DB = {
    1: {"name": "Ada Lovelace", "email": "ada@example.com", "posts": 12, "last_login": "2026-07-01"},
    2: {"name": "Alan Turing", "email": "alan@example.com", "posts": 5, "last_login": "2026-06-28"},
}


@app.get("/users")
def list_users():
    out = []
    for uid, u in _DB.items():
        out.append({"id": uid, "name": u["name"], "email": u["email"]})
    return out


@app.get("/users/{user_id}")
def get_user(user_id: int):
    if user_id not in _DB:
        raise HTTPException(404)
    u = _DB[user_id]
    return {"id": user_id, "name": u["name"], "email": u["email"]}
