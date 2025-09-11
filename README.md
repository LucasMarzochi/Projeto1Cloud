# Tuesday.com (Projeto 1 — Opção 2)  
Frontend (Streamlit) + App (FastAPI) + Database (MySQL) em 3 VMs Vagrant

Este repositório entrega a arquitetura pedida na **Opção 2** dos slides: três VMs isoladas por rede, provisionadas automaticamente, com frontend acessível pelo host e APP/DB apenas na rede interna.

---

## 🔎 Visão geral

- **frontend**: Streamlit (UI)  
  - NIC host-only: `192.168.40.10` (porta **8501**)  
  - NIC interna: `192.168.90.10`  
  - Port-forward: **host:18000 → guest:8501**  
  - UFW: **bloqueia** acesso à 8501 vindo de `192.168.90.0/24` (rede interna); **permite** demais origens

- **app**: FastAPI (serviço de autenticação e tarefas)  
  - NIC interna: `192.168.90.20` (porta **8001**)  
  - UFW: **permite só** `192.168.90.0/24` em 8001

- **database**: MySQL (persistência)  
  - NIC interna: `192.168.90.30` (porta **3306**)  
  - `bind-address=192.168.90.30`  
  - UFW: **permite só** `192.168.90.20` (VM app) em 3306

---

## 📁 Estrutura do repositório

```
.
├─ Vagrantfile
├─ frontend/
│  ├─ app.py                         # app Streamlit (multipáginas)
│  ├─ pages/
│  │  └─ 01_Arquitetura_Status.py    # página de status/diagrama ao vivo
│  ├─ requirements.txt│
│  └─ .env                           # Criar e adicionar API_URL = http://192.168.90.20:8001
├─ app/
│  ├─ main.py                        # FastAPI (auth + tasks)
│  └─ requirements.txt
└─ database/
   └─ init.sql
```

---

## ✅ Pré-requisitos

- VMware (ou provedor VMware do Vagrant) instalado  
- Vagrant instalado  
- Porta **18000** livre no host (ou ajuste no `Vagrantfile`)

---

## 🚀 Como subir

```bash
Clone o repositório
Pelo terminal vá ate a pasta em que se localiza a Vagrantfile
Quando estiver dentro dela execute:
vagrant up - Para subir as vms
```

**Acessos:**
- **Host** (este computador): `http://127.0.0.1:18000`
- **Outra máquina na mesma rede**: `http://IP-DO-SEU-MAC:18000`
- **Direto na NIC host-only da VM** (host): `http://192.168.40.10:8501`  
  *(A rede interna 90.x é isolada por firewall e não deve ser usada para o navegador.)*

---

## 🔐 API (FastAPI)

- **/health** → `{"status":"ok","service":"api","db_host": "..."}`
- **/auth/register** (POST) → `{accessToken: "..."}`
- **/auth/login** (POST) → `{accessToken: "..."}`
- **/api/tasks** (GET, POST) — exige `Authorization: Bearer <token>`
- **/api/tasks/{id}** (PUT, DELETE) — exige JWT

**Variáveis (systemd do app)**:
```
DB_HOSTS=database,192.168.90.30
DB_USER=app_user
DB_PASS=app_pass
DB_NAME=app_db
JWT_SECRET=change-me
```

---

## 🖥️ Frontend (Streamlit)

### Páginas
1. **Início**  
   - Nome da aplicação (Tuesday.com)  
   - Status “API ok / DB conectado”  
   - Botão para Login/Registro  
2. **Login/Registro**  
   - Cria conta ou faz login  
   - Ao sucesso, redireciona para “Tarefas”  
   - Topo mostra **e-mail** da conta com menu para **Sair**
3. **Tarefas**  
   - Criar tarefa: título, datas/horas, descrição e **prioridade** (Baixa/Média/Alta)  
   - Listagem em **tabela**  

### Página de arquitetura/status
- `frontend/pages/01_Arquitetura_Status.py` exibe:
  - `API_URL` efetiva
  - Resultado de `/health` (API/DB)
  - Diagrama ASCII da topologia

---

## 🧪 Teste rápido (fim-a-fim)

1) Abra `http://127.0.0.1:18000`  
2) Home → **Login/Registro**, crie conta → redirecione para **Tarefas**  
3) Crie tarefa (preencha título/datas/horas/descrição/prioridade)  
4) Veja na **tabela**  

---

## 🛠️ Verificações (CLI)

**Serviços:**
```bash
vagrant ssh frontend -c "systemctl --no-pager -l status streamlit-frontend"
vagrant ssh app      -c "systemctl --no-pager -l status fastapi-api"
vagrant ssh database -c "systemctl --no-pager -l status mysql"
```

**Portas ouvindo:**
```bash
vagrant ssh frontend -c "ss -ltnp | grep 8501 || true"
vagrant ssh app      -c "ss -ltnp | grep 8001 || true"
vagrant ssh database -c "ss -ltnp | grep 3306 || true"
```

**UFW (firewall):**
```bash
vagrant ssh frontend -c "sudo ufw status numbered"
vagrant ssh app      -c "sudo ufw status numbered"
vagrant ssh database -c "sudo ufw status numbered"
```

**Health & DB:**
```bash
vagrant ssh app      -c "curl -s http://127.0.0.1:8001/health"
vagrant ssh database -c "sudo mysql -e 'SHOW DATABASES; USE app_db; SHOW TABLES;'"
```

---

## 🌐 Acesso por outra máquina (LAN)

Já está habilitado:  
`Vagrantfile` tem `host_ip: "0.0.0.0"` no port-forward do frontend.

- No **outro dispositivo**: abra `http://IP-DO-SEU-MAC:18000`
- Garanta que o **firewall do macOS** permite conexões de entrada para VMware/Vagrant
- Evite redes com “AP Isolation” (clientes não se enxergam)

> A API e o DB **não** são expostos à LAN — o frontend fala com eles pela **rede interna 192.168.90.0/24**.

---

## 📌 Conformidade com a avaliação

- **Funcionamento da solução**: `vagrant up` sobe tudo; UI → login/registro → criar tarefas; persistência no MySQL.  
- **Aderência à arquitetura**: 3 VMs, frontend exposto, APP/DB internos.  
- **Setups de rede**: vmnet2 (40.x) para host-only; vmnet3 (90.x) interna; port-forward 18000→8501; firewall coerente.  
- **Setups dos componentes**: provisionamento automático (apt+venv+pip), unit files systemd, variáveis de ambiente, `bind-address` do MySQL, UFW por VM.

---
