import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

# Garante que a raiz do projeto esteja no PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Config do banco, compatível com o workflow
DB_USER = os.getenv("DB_USER", "app_user")
DB_PASS = os.getenv("DB_PASS", "app_pass")
DB_NAME = os.getenv("DB_NAME", "app_db")
DB_HOST = os.getenv("DB_HOSTS", "127.0.0.1").split(",")[0]
DB_PORT = int(os.getenv("DB_PORT", "3306"))

DB_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    "?charset=utf8mb4"
)

from app import main as app  # noqa: E402


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(DB_URL, future=True)
    yield engine
    engine.dispose()


@pytest.fixture
def client(db_engine):
    # Limpa tabelas antes de cada teste de integração
    with db_engine.begin() as conn:
        conn.execute(text("DELETE FROM tasks"))
        conn.execute(text("DELETE FROM users"))
    return TestClient(app.app)


@pytest.mark.integration
def test_health_retorna_ok_ou_degraded(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "api"
    assert data["status"] in {"ok", "degraded"}


@pytest.mark.integration
def test_fluxo_register_e_login_funciona(client):
    email = "integ_user@example.com"
    senha = "senha123"

    # Registro
    r1 = client.post(
        "/auth/register",
        json={"name": "User Integra", "email": email, "password": senha},
    )
    assert r1.status_code == 200
    token1 = r1.json().get("accessToken")
    assert token1

    # Login
    r2 = client.post("/auth/login", json={"email": email, "password": senha})
    assert r2.status_code == 200
    token2 = r2.json().get("accessToken")
    assert token2
    assert token1 != "" and token2 != ""


@pytest.mark.integration
def test_crud_de_tasks(client):
    email = "tasks_user@example.com"
    senha = "senha123"

    # Cria usuário
    r = client.post(
        "/auth/register",
        json={"name": "User Tasks", "email": email, "password": senha},
    )
    assert r.status_code == 200
    token = r.json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    # Cria tarefa
    payload = {
        "title": "Tarefa integ",
        "description": "Teste integração",
        "start_at": "2025-01-01T10:00:00",
        "end_at": "2025-01-01T11:00:00",
        "status": "todo",
        "priority": "medium",
    }
    r_create = client.post("/api/tasks", json=payload, headers=headers)
    assert r_create.status_code in (200, 201)
    task_id = r_create.json()["id"]

    # Lista tarefas
    r_list = client.get("/api/tasks", headers=headers)
    assert r_list.status_code == 200
    tasks = r_list.json()
    assert any(t["id"] == task_id for t in tasks)

    # Atualiza tarefa
    payload_update = dict(payload)
    payload_update["title"] = "Tarefa integ atualizada"
    r_upd = client.put(f"/api/tasks/{task_id}", json=payload_update, headers=headers)
    assert r_upd.status_code == 200
    assert r_upd.json()["id"] == task_id

    # Deleta tarefa
    r_del = client.delete(f"/api/tasks/{task_id}", headers=headers)
    assert r_del.status_code == 204

    # Confere que sumiu
    r_list2 = client.get("/api/tasks", headers=headers)
    assert r_list2.status_code == 200
    tasks2 = r_list2.json()
    assert all(t["id"] != task_id for t in tasks2)
