import os
import json
import requests
import streamlit as st
from datetime import datetime, timedelta, time as dtime

# --------- .env ----------
def load_env():
    path = "/srv/frontend/.env"
    if os.path.exists(path):
        for line in open(path, "r", encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
load_env()

API_URL = os.getenv("API_URL", "http://192.168.90.20:8001").rstrip("/")

st.set_page_config(page_title="Tuesday.com", layout="wide")

if "route" not in st.session_state:
    st.session_state.route = "home"
if "token" not in st.session_state:
    st.session_state.token = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "show_account_menu" not in st.session_state:
    st.session_state.show_account_menu = False
if "tasks_cache" not in st.session_state:
    st.session_state.tasks_cache = []

def safe_rerun():
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            pass

def goto(route: str):
    st.session_state.route = route
    safe_rerun()

def auth_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.token else {}

def api(method, path, **kwargs):
    headers = kwargs.pop("headers", {})
    headers.update(auth_headers())
    return requests.request(method, f"{API_URL}{path}", headers=headers, timeout=6, **kwargs)

def iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat(timespec="seconds")

def do_logout():
    st.session_state.token = None
    st.session_state.user_email = None
    st.session_state.tasks_cache = []
    st.session_state.show_account_menu = False
    goto("home")

def topbar(show_nav: bool):
    c1, csp, c2 = st.columns([6, 3, 3])
    with c1:
        st.markdown("### **Tuesday.com**")

    with c2:
        if show_nav:
            nav_cols = st.columns([1, 1, 2])
            with nav_cols[0]:
                if st.button("Início", key="btn_home_top"):
                    goto("home")
            with nav_cols[1]:
                if (not st.session_state.token) and st.button("Login / Registro", key="btn_auth_top"):
                    goto("auth")

            with nav_cols[2]:
                if st.session_state.token:
                    label = f"👤 {st.session_state.user_email or 'Conta'} ▾"
                    if st.button(label, key="btn_account"):
                        st.session_state.show_account_menu = not st.session_state.show_account_menu
                        safe_rerun()
                    if st.session_state.show_account_menu:
                        st.write("")  # pequeno espaçamento
                        if st.button("Sair da conta", key="btn_logout"):
                            do_logout()

def page_home():
    topbar(show_nav=False)

    st.markdown("## Bem-vindo ao **Tuesday.com**")

    st.markdown("---")
    st.write("Faça login ou crie sua conta para gerenciar suas tarefas.")
    if st.button("Ir para Login/Registro ➜", key="btn_go_auth"):
        goto("auth")

def page_auth():
    topbar(show_nav=False)
    st.markdown("## Autenticação")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Criar conta")
        r_name = st.text_input("Nome", key="r_name")
        r_email = st.text_input("E-mail", key="r_email")
        r_pass = st.text_input("Senha", type="password", key="r_pass")
        if st.button("Criar conta", key="btn_register"):
            if not (r_name and r_email and r_pass):
                st.error("Preencha nome, e-mail e senha.")
            else:
                try:
                    r = api("POST", "/auth/register",
                            json={"name": r_name, "email": r_email, "password": r_pass})
                    if r.ok:
                        try:
                            data = r.json()
                        except Exception:
                            data = json.loads(r.text)
                        st.session_state.token = data.get("accessToken")
                        st.session_state.user_email = r_email.strip().lower()
                        if st.session_state.token:
                            st.success("Conta criada! Redirecionando…")
                            goto("tasks")
                        else:
                            st.error("Resposta da API sem token.")
                    else:
                        st.error(f"Erro: {r.status_code} {r.text}")
                except Exception as e:
                    st.error(f"Falha: {e}")

    with col2:
        st.markdown("### Entrar")
        l_email = st.text_input("E-mail (login)", key="l_email")
        l_pass  = st.text_input("Senha (login)", type="password", key="l_pass")
        c = st.columns(2)
        if c[0].button("Entrar", key="btn_login"):
            if not (l_email and l_pass):
                st.error("Informe e-mail e senha.")
            else:
                try:
                    r = api("POST", "/auth/login", json={"email": l_email, "password": l_pass})
                    if r.ok:
                        try:
                            data = r.json()
                        except Exception:
                            data = json.loads(r.text)
                        st.session_state.token = data.get("accessToken")
                        st.session_state.user_email = l_email.strip().lower()
                        if st.session_state.token:
                            st.success("Conectado! Redirecionando…")
                            goto("tasks")
                        else:
                            st.error("Resposta da API sem token.")
                    else:
                        st.error(f"Erro: {r.status_code} {r.text}")
                except Exception as e:
                    st.error(f"Falha: {e}")
        if c[1].button("Voltar ao Início", key="btn_back_home"):
            goto("home")

def page_tasks():
    topbar(show_nav=True)
    st.markdown("## Minhas tarefas")

    if not st.session_state.token:
        st.warning("Você precisa estar autenticado.")
        if st.button("Ir para Login/Registro", key="btn_to_auth_from_tasks"):
            goto("auth")
        return

    now = datetime.now().replace(second=0, microsecond=0)
    plus1 = now + timedelta(hours=1)

    with st.form("form_task", clear_on_submit=True):
        t_title = st.text_input("Título", "")

        c1, c2 = st.columns(2)
        t_start_d = c1.date_input("Início - Data", now.date())
        t_start_t = c2.time_input("Início - Hora", now.time())

        c3, c4 = st.columns(2)
        t_end_d   = c3.date_input("Fim - Data", plus1.date())
        t_end_t   = c4.time_input("Fim - Hora", plus1.time())

        t_desc = st.text_area("Descrição (opcional)", "")

        prioridades = {
            "Prioridade baixa": "low",
            "Prioridade média": "medium",
            "Prioridade alta": "high",
        }
        pr_label = st.selectbox("Prioridade", list(prioridades.keys()), index=1)
        pr_value = prioridades[pr_label]

        submitted = st.form_submit_button("Criar tarefa")

        if submitted:
            start_dt = datetime.combine(t_start_d, dtime(t_start_t.hour, t_start_t.minute))
            end_dt   = datetime.combine(t_end_d,   dtime(t_end_t.hour,   t_end_t.minute))

            if end_dt <= start_dt:
                end_dt = start_dt + timedelta(hours=1)
                st.info("Ajustei o 'Fim' para 1 hora após o 'Início'.")

            if not t_title.strip():
                st.error("Informe um título.")
            else:
                payload = {
                    "title": t_title.strip(),
                    "start_at": iso(start_dt),
                    "end_at": iso(end_dt),
                    "description": t_desc or None,
                    "status": "todo",
                    "priority": pr_value,
                }
                try:
                    r = api("POST", "/api/tasks", json=payload)
                    if r.status_code in (200, 201):
                        st.success("Tarefa criada!")
                        st.session_state.tasks_cache = []
                        safe_rerun()
                    else:
                        st.error(f"Erro: {r.status_code} {r.text}")
                except Exception as e:
                    st.error(f"Falha: {e}")

    if not st.session_state.tasks_cache:
        r = api("GET", "/api/tasks")
        if r.ok:
            try:
                st.session_state.tasks_cache = r.json()
            except Exception:
                st.session_state.tasks_cache = json.loads(r.text or "[]")
        else:
            st.error(f"Erro: {r.status_code} {r.text}")

    tasks = st.session_state.tasks_cache or []
    if not tasks:
        st.write("(Sem tarefas)")
    else:
        pt_map = {"low": "baixa", "medium": "média", "high": "alta"}
        rows = []
        for t in tasks:
            rows.append({
                "Título": t.get("title", ""),
                "Início": t.get("start_at", ""),
                "Fim": t.get("end_at", ""),
                "Status": t.get("status", "todo"),
                "Prioridade": pt_map.get(t.get("priority", "medium"), t.get("priority", "")),
                "Descrição": t.get("description", "") or "",
            })
        st.dataframe(rows, use_container_width=True)

    st.markdown("---")
    c = st.columns(2)
    if c[0].button("Atualizar lista", key="btn_refresh_tasks"):
        st.session_state.tasks_cache = []
        safe_rerun()

route = st.session_state.route
if route == "home":
    page_home()
elif route == "auth":
    page_auth()
else:
    page_tasks()
