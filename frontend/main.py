from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import httpx
import os

APP_URL = os.getenv("APP_URL", "http://app:3000")

app = FastAPI(title="Frontend (FastAPI)")

@app.get("/health")
def health():
    return {"status": "ok", "service": "frontend-fastapi"}

@app.get("/", response_class=HTMLResponse)
def home():
    # Página simples que consome o Node internamente e renderiza HTML
    try:
        todos = httpx.get(f"{APP_URL}/api/todos", timeout=5).json()
    except Exception as e:
        todos = []
    items = "".join(f"<li>{t['id']}: {t['title']} - {'✅' if t['done'] else '❌'}</li>" for t in todos)
    html = f"""
    <html>
      <head><meta charset="utf-8"><title>Frontend (FastAPI)</title></head>
      <body>
        <h1>Todos (via Node)</h1>
        <ul>{items or '<li>(vazio)</li>'}</ul>
        <p><a href="/health">/health</a></p>
      </body>
    </html>
    """
    return HTMLResponse(html)

@app.get("/todos", response_class=JSONResponse)
def todos_proxy():
    # Endpoint JSON que apenas faz proxy para o Node (útil para testes)
    try:
        r = httpx.get(f"{APP_URL}/api/todos", timeout=5)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))
