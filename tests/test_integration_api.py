import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# configura o banco para que seja compatível com o workflow
DB_USER = os.getenv("DB_USER", "app_user")
DB_PASS = os.getenv("DB_PASS", "app_pass")
DB_NAME = os.getenv("DB_NAME", "app_db")
DB_HOST = os.getenv("DB_HOSTS", "127.0.0.1").split(",")[0]
DB_PORT = int(os.getenv("DB_PORT", "3306"))

DB_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    "?charset=utf8mb4"
)

from app import main as app 


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

# faz o teste da health garantindo que consegue se comunicar com o banco
@pytest.mark.integration
def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "api"
    assert data["status"] in {"ok", "degraded"}

# testa se o registro realmente adiciona um novo usuário no BD e se o login consegue buscar o usuário no banco e validar senha
@pytest.mark.integration
def test_fluxo_register_e_login(client):
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

# faz um teste "completo" da aplicacao
# cria um novo usuario ele entao cria uma tarefa e verifica se a tarefa esta na lista de tarefas
# depois atuliza a tarefa, deleta a tarefa e confere que a tarefa realmente sumiu
@pytest.mark.integration
def test_funcionalidades_app(client):
    email = "tasks_user@example.com"
    senha = "senha123"

    cria_user = client.post(
        "/auth/register",
        json={"name": "User Tasks", "email": email, "password": senha},
    )
    assert cria_user.status_code == 200
    token = cria_user.json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "title": "Tarefa teste de integracao",
        "description": "Teste integração",
        "start_at": "2025-01-01T10:00:00",
        "end_at": "2025-01-01T11:00:00",
        "status": "todo",
        "priority": "medium",
    }
    cria_tarefa_teste = client.post("/api/tasks", json=payload, headers=headers)
    assert cria_tarefa_teste.status_code in (200, 201)
    task_id = cria_tarefa_teste.json()["id"]

    verifica_lista_tarefas = client.get("/api/tasks", headers=headers)
    assert verifica_lista_tarefas.status_code == 200
    tasks = verifica_lista_tarefas.json()
    assert any(t["id"] == task_id for t in tasks)

    payload_update = dict(payload)
    payload_update["title"] = "Tarefa teste de integracao atualizada"
    r_upd = client.put(f"/api/tasks/{task_id}", json=payload_update, headers=headers)
    assert r_upd.status_code == 200
    assert r_upd.json()["id"] == task_id

    deleta_tarefa = client.delete(f"/api/tasks/{task_id}", headers=headers)
    assert deleta_tarefa.status_code == 204

    confere_tarefa_deletada = client.get("/api/tasks", headers=headers)
    assert confere_tarefa_deletada.status_code == 200
    tasks2 = confere_tarefa_deletada.json()
    assert all(t["id"] != task_id for t in tasks2)
