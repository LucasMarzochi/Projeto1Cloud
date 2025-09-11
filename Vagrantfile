# Vagrantfile — Tuesday (Frontend: Streamlit | App: FastAPI | DB: MySQL)
Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-22.04"

  # ---------------- FRONTEND (Streamlit) ----------------
  config.vm.define "frontend" do |fe|
    fe.vm.hostname = "frontend"

    # NIC externa (host-only) e NIC interna (intra-VMs)
    fe.vm.network "private_network",
      ip: "192.168.40.10", netmask: "255.255.255.0", vmware__netname: "vmnet2"
    fe.vm.network "private_network",
      ip: "192.168.90.10", netmask: "255.255.255.0", vmware__netname: "vmnet3"

    # Port-forward para acessar de qualquer computador na mesma rede com meu ip
    fe.vm.network "forwarded_port",
      guest: 8501, host: 18000, host_ip: "0.0.0.0", auto_correct: true

    # Pasta sincronizada
    fe.vm.synced_folder "./frontend", "/srv/frontend",
      create: true, owner: "vagrant", group: "vagrant"

    fe.vm.provider "vmware_desktop" do |v|
      v.gui    = true
      v.memory = "2048"
      v.cpus   = 2
      v.vmx["displayName"] = "Tuesday - Frontend"
    end

    fe.vm.provision "shell", inline: <<-'SH'
      set -euxo pipefail
      export DEBIAN_FRONTEND=noninteractive
      export NEEDRESTART_MODE=a

      apt-get update
      apt-get install -y python3 python3-venv python3-pip ufw ca-certificates

      # venv do Streamlit
      install -d -m 0755 /opt/venvs/frontend
      [ -x /opt/venvs/frontend/bin/python ] || python3 -m venv /opt/venvs/frontend
      /opt/venvs/frontend/bin/pip install --upgrade pip
      /opt/venvs/frontend/bin/pip install streamlit requests python-dotenv

      # Nomes internos
      grep -q "192.168.90.20 app" /etc/hosts || echo "192.168.90.20 app" >> /etc/hosts
      grep -q "192.168.90.30 database" /etc/hosts || echo "192.168.90.30 database" >> /etc/hosts

      # .env do frontend: NÃO sobrescreve se você já criou
      if [ ! -f /srv/frontend/.env ]; then
        cat >/srv/frontend/.env <<'EOF'
API_URL=http://192.168.90.20:8001
EOF
      fi

      # App mínimo se faltar (evita serviço quebrar em pasta vazia)
      if [ ! -f /srv/frontend/app.py ]; then
        cat >/srv/frontend/app.py <<'PY'
import os, requests, streamlit as st
API_URL = os.getenv("API_URL", "http://192.168.90.20:8001").rstrip("/")
st.set_page_config(page_title="Tuesday", layout="wide")
st.title("Tuesday — Frontend")
with st.expander("Status dos serviços", expanded=True):
    try:
        st.json(requests.get(f"{API_URL}/health", timeout=3).json())
        st.success(f"API OK em {API_URL}")
    except Exception as e:
        st.error(f"API offline? {e}")
PY
      fi

      # systemd do Streamlit
      cat >/etc/systemd/system/streamlit-frontend.service <<'EOF'
[Unit]
Description=Tuesday Frontend (Streamlit)
After=network-online.target
Wants=network-online.target

[Service]
User=vagrant
WorkingDirectory=/srv/frontend
EnvironmentFile=-/srv/frontend/.env
Environment=PATH=/opt/venvs/frontend/bin
ExecStart=/opt/venvs/frontend/bin/streamlit run /srv/frontend/app.py --server.port=8501 --server.address=0.0.0.0
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

      systemctl daemon-reload
      systemctl enable --now streamlit-frontend || true

      # Firewall: abrir 8501 (via vmnet2) e SSH
      ufw --force reset
      ufw default deny incoming
      ufw default allow outgoing
      ufw allow 22/tcp
      ufw allow from 192.168.40.0/24 to any port 8501 proto tcp
      # Alguns providers fazem forward como conexão local; garanta também a porta em geral:
      ufw allow 8501/tcp
      ufw --force enable
    SH
  end

  # ---------------- APP (FastAPI) ----------------
  config.vm.define "app" do |app|
    app.vm.hostname = "app"

    # Apenas rede interna
    app.vm.network "private_network",
      ip: "192.168.90.20", netmask: "255.255.255.0", vmware__netname: "vmnet3"

    # Pasta sincronizada
    app.vm.synced_folder "./app", "/srv/app",
      create: true, owner: "vagrant", group: "vagrant"

    app.vm.provider "vmware_desktop" do |v|
      v.gui    = true
      v.memory = "2048"
      v.cpus   = 2
      v.vmx["displayName"] = "Tuesday - App (FastAPI)"
    end

    app.vm.provision "shell", inline: <<-'SH'
      set -euxo pipefail
      export DEBIAN_FRONTEND=noninteractive
      export NEEDRESTART_MODE=a

      apt-get update
      apt-get install -y python3 python3-venv python3-pip build-essential python3-dev libssl-dev libffi-dev ufw ca-certificates

      install -d -m 0755 /opt/venvs/api
      [ -x /opt/venvs/api/bin/python ] || python3 -m venv /opt/venvs/api
      /opt/venvs/api/bin/pip install --upgrade pip
      /opt/venvs/api/bin/pip install fastapi "uvicorn[standard]" sqlalchemy pymysql \
        "python-jose[cryptography]" "passlib[bcrypt]" python-dotenv "pydantic[email]"

      # hosts internos
      grep -q "192.168.90.30 database" /etc/hosts || echo "192.168.90.30 database" >> /etc/hosts

      # App mínimo se faltar
      if [ ! -f /srv/app/main.py ]; then
        cat >/srv/app/main.py <<'PY'
from fastapi import FastAPI
app = FastAPI(title="Tuesday API")
@app.get("/health")
def health(): return {"status":"ok","service":"api"}
PY
      fi

      # systemd da API
      cat >/etc/systemd/system/fastapi-api.service <<'EOF'
[Unit]
Description=Tuesday FastAPI API
After=network-online.target
Wants=network-online.target

[Service]
User=vagrant
WorkingDirectory=/srv/app
Environment=PATH=/opt/venvs/api/bin
Environment=DB_HOST=database
Environment=DB_USER=app_user
Environment=DB_PASS=app_pass
Environment=DB_NAME=app_db
Environment=JWT_SECRET=change-me
ExecStart=/opt/venvs/api/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

      systemctl daemon-reload
      systemctl enable --now fastapi-api || true

      # Firewall: só rede interna pode acessar 8001
      ufw --force reset
      ufw default deny incoming
      ufw default allow outgoing
      ufw allow 22/tcp
      ufw allow from 192.168.90.0/24 to any port 8001 proto tcp
      ufw --force enable
    SH
  end

  # ---------------- DATABASE (MySQL) ----------------
  config.vm.define "database" do |db|
    db.vm.hostname = "database"

    db.vm.network "private_network",
      ip: "192.168.90.30", netmask: "255.255.255.0", vmware__netname: "vmnet3"

    db.vm.synced_folder "./database", "/srv/database",
      create: true, owner: "vagrant", group: "vagrant"

    db.vm.provider "vmware_desktop" do |v|
      v.gui    = true
      v.memory = "1536"
      v.cpus   = 1
      v.vmx["displayName"] = "Tuesday - Database (MySQL)"
    end

    db.vm.provision "shell", inline: <<-'SH'
      set -euxo pipefail
      export DEBIAN_FRONTEND=noninteractive
      export NEEDRESTART_MODE=a

      apt-get update
      apt-get install -y mysql-server ufw ca-certificates

      # Bind apenas no IP interno
      CFG="/etc/mysql/mysql.conf.d/mysqld.cnf"
      if grep -q "^bind-address" "$CFG"; then
        sed -i 's/^bind-address.*/bind-address = 192.168.90.30/' "$CFG"
      else
        echo "bind-address = 192.168.90.30" >> "$CFG"
      fi
      systemctl restart mysql

      # Banco e usuário
      mysql -uroot -e "CREATE DATABASE IF NOT EXISTS app_db;"
      mysql -uroot -e "CREATE USER IF NOT EXISTS 'app_user'@'192.168.90.%' IDENTIFIED BY 'app_pass';"
      mysql -uroot -e "GRANT ALL PRIVILEGES ON app_db.* TO 'app_user'@'192.168.90.%'; FLUSH PRIVILEGES;"

      # Import opcional
      [ -f /srv/database/init.sql ] && mysql -uapp_user -papp_pass app_db < /srv/database/init.sql || true

      # Firewall: só o APP (e opcionalmente o frontend) acessam 3306
      ufw --force reset
      ufw default deny incoming
      ufw default allow outgoing
      ufw allow 22/tcp
      ufw allow from 192.168.90.20 to any port 3306 proto tcp
      # ufw allow from 192.168.90.10 to any port 3306 proto tcp  # descomente se o frontend precisar acessar o DB
      ufw --force enable
    SH
  end
end
