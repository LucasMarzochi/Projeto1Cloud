import os, json, requests, streamlit as st

# Lê .env do frontend
def load_env():
    p = "/srv/frontend/.env"
    if os.path.exists(p):
        for line in open(p, "r", encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
load_env()

API_URL = os.getenv("API_URL", "http://192.168.90.20:8001").rstrip("/")

st.set_page_config(page_title="Arquitetura & Status", layout="wide")
st.title("Arquitetura & Status — Tuesday.com")

col1, col2 = st.columns(2)
with col1:
    st.subheader("Configuração efetiva")
    st.markdown(f"- **API_URL (frontend → API):** `{API_URL}`")
    st.markdown("- **VMs (padrão do projeto):**")
    st.code(
        "frontend  -> vmnet2 192.168.40.10 : 8501 (port-forward :18000)\n"
        "frontend  -> vmnet3 192.168.90.10 (NIC interna)\n"
        "app (API) -> vmnet3 192.168.90.20 : 8001\n"
        "database  -> vmnet3 192.168.90.30 : 3306",
        language="text"
    )

with col2:
    st.subheader("Status ao vivo")
    try:
        r = requests.get(f"{API_URL}/health", timeout=3)
        try:
            h = r.json()
        except Exception:
            h = json.loads(r.text or "{}")
        status = str(h.get("status","")).lower()
        db_host = h.get("db_host", "desconhecido")
        if status == "ok":
            st.success("API: OK")
        else:
            st.warning(f"API: {status or 'indefinido'}")
        st.info(f"Database conectado: **{db_host}**")
    except Exception as e:
        st.error(f"API offline? {e}")

st.subheader("Diagrama (ASCII)")
st.code(
r"""
Usuário ──HTTP──> Host (seu Mac) :18000 ──> Frontend (Streamlit)
                                    │
                                    └── vmnet2: 192.168.40.10:8501

Rede interna vmnet3 (192.168.90.0/24):
  Frontend (192.168.90.10) ──HTTP:8001──> App FastAPI (192.168.90.20) ──TCP:3306──> MySQL (192.168.90.30)
""",
language="text"
)
