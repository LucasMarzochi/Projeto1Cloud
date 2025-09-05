import os
import requests
import streamlit as st
from datetime import datetime

API_URL = os.getenv("API_URL", "http://app:8001")

st.set_page_config(page_title="Tuesday (Streamlit)", layout="wide")
st.title("Tuesday – Frontend (Streamlit)")

# ---------------- Session helpers ----------------
if "token" not in st.session_state:
    st.session_state.token = None

def auth_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.token else {}

def iso(dt_date, dt_time):
    """Combina inputs de date+time em ISO 8601 (YYYY-MM-DDTHH:MM:SS)."""
    return f"{dt_date}T{dt_time}:00"

# ---------------- Health ----------------
with st.expander("Status dos serviços", expanded=True):
    try:
        h = requests.get(f"{API_URL}/health", timeout=3).json()
        st.success(f"API: {h}")
    except Exception as e:
        st.error(f"API offline? {e}")

# ---------------- Auth ----------------
st.subheader("Autenticação")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Registrar**")
    r_name = st.text_input("Nome", key="r_name")
    r_email = st.text_input("E-mail", key="r_email")
    r_pass = st.text_input("Senha", type="password", key="r_pass")
    if st.button("Criar conta"):
        try:
            r = requests.post(f"{API_URL}/auth/register",
                              json={"name": r_name, "email": r_email, "password": r_pass},
                              timeout=5)
            if r.status_code in (200, 201):
                st.session_state.token = r.json()["accessToken"]
                st.success("Conta criada e conectado!")
            else:
                st.error(f"Erro: {r.status_code} {r.text}")
        except Exception as e:
            st.error(f"Falha: {e}")

with col2:
    st.markdown("**Login**")
    l_email = st.text_input("E-mail (login)", key="l_email")
    l_pass = st.text_input("Senha (login)", type="password", key="l_pass")
    cols_login = st.columns(2)
    if cols_login[0].button("Entrar"):
        try:
            r = requests.post(f"{API_URL}/auth/login",
                              json={"email": l_email, "password": l_pass},
                              timeout=5)
            if r.status_code == 200:
                st.session_state.token = r.json()["accessToken"]
                st.success("Conectado!")
            else:
                st.error(f"Erro: {r.status_code} {r.text}")
        except Exception as e:
            st.error(f"Falha: {e}")
    if cols_login[1].button("Sair"):
        st.session_state.token = None
        st.info("Sessão encerrada.")

# ---------------- Tasks ----------------
st.subheader("Minhas tarefas")
if not st.session_state.token:
    st.info("Faça login ou cadastre-se para ver/criar tarefas.")
else:
    # Form de criação
    with st.form("form_task", clear_on_submit=True):
        t_title = st.text_input("Título", "")
        c1, c2 = st.columns(2)
        t_start_d = c1.date_input("Início - Data", datetime.now().date())
        t_start_t = c2.time_input("Início - Hora", datetime.now().time().replace(second=0, microsecond=0))
        c3, c4 = st.columns(2)
        t_end_d = c3.date_input("Fim - Data", datetime.now().date())
        t_end_t = c4.time_input("Fim - Hora", (datetime.now()).time().replace(second=0, microsecond=0))
        t_desc = st.text_area("Descrição (opcional)", "")
        submitted = st.form_submit_button("Criar tarefa")
        if submitted:
            payload = {
                "title": t_title,
                "start_at": iso(t_start_d.isoformat(), t_start_t.strftime("%H:%M")),
                "end_at": iso(t_end_d.isoformat(), t_end_t.strftime("%H:%M")),
                "description": t_desc or None,
                "status": "todo",
                "priority": "medium"
            }
            try:
                r = requests.post(f"{API_URL}/api/tasks", json=payload, headers=auth_headers(), timeout=5)
                if r.status_code in (200, 201):
                    st.success("Tarefa criada!")
                else:
                    st.error(f"Erro: {r.status_code} {r.text}")
            except Exception as e:
                st.error(f"Falha: {e}")

    # Listagem
    try:
        r = requests.get(f"{API_URL}/api/tasks", headers=auth_headers(), timeout=5)
        if r.status_code == 200:
            tasks = r.json()
            if not tasks:
                st.write("(Sem tarefas)")
            else:
                for t in tasks:
                    st.markdown(f"- **{t['title']}** — {t['start_at']} → {t['end_at']} — {t['status']} / {t['priority']}")
        else:
            st.error(f"Erro: {r.status_code} {r.text}")
    except Exception as e:
        st.error(f"Falha: {e}")
