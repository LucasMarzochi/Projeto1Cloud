import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError
from jose import jwt
# os unit tests testam algumas lógicas da api de maneira isolada sem depender da infraestrutura

# Garante que a raiz do projeto esteja no PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Define o segredo ANTES de importar o módulo principal
os.environ.setdefault("JWT_SECRET", "test-secret")

from app import main as app  # noqa: E402



@pytest.mark.unit
# cria um email que nao seria aceito normalmente(letras maiusculas) e espera que o modelo o normalize(register)
def test_registerin_normaliza_email():
    data = app.RegisterIn(
        name="User",
        email="  TESTE@Example.COM  ",
        password="123456",
    )
    assert data.email == "teste@example.com"

# faz a mesma coisa que o anterior poré agora para a parte do login
@pytest.mark.unit
def test_loginin_normaliza_email():
    data = app.LoginIn(
        email="  Foo@Bar.Com ",
        password="abc",
    )
    assert data.email == "foo@bar.com"

# tenta se registrar com um email inválido, espera que de erro
@pytest.mark.unit
def test_registerin_email_invalido_dispara_erro():
    with pytest.raises(ValidationError):
        app.RegisterIn(
            name="User",
            email="email-invalido",
            password="123",
        )

# testa o hash da senha
@pytest.mark.unit
def test_hash_pw_e_check_pw_sucesso():
    senha = "minha-senha-super"
    h = app.hash_pw(senha)

    assert h != senha # ve se nao esta mostrando a senha realmente
    assert app.check_pw(senha, h) is True # garante que a parte de hash da senha esta funcionando

# cria uma senha e faz o teste com uma diferente para garantir que nao é possivel acessar sem a senha correta
@pytest.mark.unit
def test_check_pw_falso_para_senha_errada():
    senha = "senha-certa"
    h = app.hash_pw(senha)

    assert app.check_pw("outra-senha", h) is False

# testa se o JWT tem as configuracoes minimas para o sistema de autenticaco funcionar
@pytest.mark.unit
def test_mk_token_contem_claims_basicos():
    user = app.User(id=42, email="user@example.com", name="User Teste")
    token = app.mk_token(user)

    decoded = jwt.decode(token, app.JWT_SECRET, algorithms=[app.JWT_ALG])

    assert decoded["sub"] == "42"
    assert decoded["email"] == "user@example.com"
    assert decoded["name"] == "User Teste"
    assert "exp" in decoded
    assert "iat" in decoded

# testa se todas as novas tarefas criadas tem defaults basicos corretos (todo e medium)
@pytest.mark.unit
def test_taskin_defaults_todo_medium():
    now = datetime.utcnow()
    ti = app.TaskIn(
        title="Tarefa teste",
        start_at=now,
        end_at=now + timedelta(hours=1),
    )

    assert ti.status == "todo"
    assert ti.priority == "medium"
