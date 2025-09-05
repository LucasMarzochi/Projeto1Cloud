Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-22.04"

  # ===================== FRONTEND (Streamlit exposto) =====================
  config.vm.define "frontend" do |fe|
    fe.vm.hostname = "frontend"

    # NAT primeiro (ajuda o forward do VMware a ficar estável)
    fe.vm.network "private_network", type: "dhcp", vmware__netname: "vmnet8"

    # Host-only externa (mantenha as vmnets que você já tem no projeto)
    fe.vm.network "private_network",
      ip: "192.168.40.10", netmask: "255.255.255.0", vmware__netname: "vmnet4"

    # Host-only interna
    fe.vm.network "private_network",
      ip: "192.168.90.10", netmask: "255.255.255.0", vmware__netname: "vmnet5"

    # Port-forward: host 127.0.0.1:18000 -> guest 0.0.0.0:8501 (Streamlit)
    fe.vm.network "forwarded_port", guest: 8501, host: 18000, auto_correct: true

    # Pasta sincronizada
    fe.vm.synced_folder "./frontend", "/srv/frontend",
      create: true, owner: "vagrant", group: "vagrant"

    fe.vm.provider "vmware_desktop" do |v|
      v.gui = true
      v.memory = "2048"
      v.cpus = 2
      v.vmx["displayName"] = "FE - Streamlit Frontend"
    end

    fe.vm.provision "shell", inline: <<-'SHELL'
      set -eux
      export DEBIAN_FRONTEND=noninteractive

      # Evitar travar no "Wait for Network to be Configured"
      mkdir -p /etc/systemd/system/systemd-networkd-wait-online.service.d
      cat >/etc/systemd/system/systemd-networkd-wait-online.service.d/override.conf <<'EOF'
[Service]
ExecStart=
ExecStart=/usr/lib/systemd/systemd-networkd-wait-online --any --timeout=15
EOF
      systemctl daemon-reload || true

      apt-get update
      apt-get install -y python3 python3-venv python3-pip git curl ufw

      # venv fora do hgfs
      install -d -m 0755 /opt/venvs/frontend
      if [ ! -f /opt/venvs/frontend/bin/activate ]; then
        python3 -m venv /opt/venvs/frontend
      fi
      /opt/venvs/frontend/bin/pip install --upgrade pip

      # Dependências do frontend (Streamlit)
      if [ -f /srv/frontend/requirements.txt ]; then
        /opt/venvs/frontend/bin/pip install -r /srv/frontend/requirements.txt
      else
        /opt/venvs/frontend/bin/pip install streamlit requests python-dotenv
      fi

      # App Streamlit mínimo, se faltar
      if [ ! -f /srv/frontend/app.py ]; then
        cat >/srv/frontend/app.py <<'PY'
import os, requests, streamlit as st
API_URL = os.getenv("API_URL", "http://app:8001")

st.set_page_config(page_title="Tuesday (Streamlit)", layout="wide")
st.title("Tuesday – Frontend (Streamlit)")

with st.expander("Estado da API (health)", expanded=True):
    try:
        h = requests.get(f"{API_URL}/health", timeout=3).json()
        st.success(h)
    except Exception as e:
        st.error(f"API offline? {e}")

st.info("Implemente login e criação de tarefas chamando a API FastAPI com Bearer Token.")
PY
      fi

      # Resolução de hosts internos
      grep -q "192.168.90.20 app" /etc/hosts || echo "192.168.90.20 app" >> /etc/hosts
      grep -q "192.168.90.30 database" /etc/hosts || echo "192.168.90.30 database" >> /etc/hosts

      # Service do Streamlit (porta 8501)
      cat >/etc/systemd/system/streamlit-frontend.service <<'EOF'
[Unit]
Description=Streamlit Frontend
After=network-online.target
Wants=network-online.target

[Service]
User=vagrant
WorkingDirectory=/srv/frontend
Environment="PATH=/opt/venvs/frontend/bin"
Environment="API_URL=http://app:8001"
ExecStart=/opt/venvs/frontend/bin/streamlit run /srv/frontend/app.py --server.port 8501 --server.address 0.0.0.0 --server.fileWatcherType none
Restart=always
RestartSec=3
KillMode=process

[Install]
WantedBy=multi-user.target
EOF

      systemctl daemon-reload
      systemctl enable streamlit-frontend.service
      systemctl restart streamlit-frontend.service || true

      # Firewall
      ufw --force reset
      ufw default deny incoming
      ufw default allow outgoing
      ufw allow 22/tcp
      ufw allow 8501/tcp
      ufw --force enable
    SHELL
  end

  # ===================== APP (FastAPI - API interna) =====================
  config.vm.define "app" do |app|
    app.vm.hostname = "app"

    # Host-only interna (mantenha conforme seu projeto)
    app.vm.network "private_network",
      ip: "192.168.90.20", netmask: "255.255.255.0", vmware__netname: "vmnet3"

    # (Opcional: debug do host) Port-forward 18001 -> 8001
    app.vm.network "forwarded_port", guest: 8001, host: 18001, auto_correct: true

    app.vm.synced_folder "./app", "/srv/app", create: true,
      owner: "vagrant", group: "vagrant"

    app.vm.provider "vmware_desktop" do |v|
      v.gui = true
      v.memory = "2048"
      v.cpus = 2
      v.vmx["displayName"] = "APP - FastAPI API"
    end

    app.vm.provision "shell", inline: <<-'SHELL'
      set -eux
      export DEBIAN_FRONTEND=noninteractive

      apt-get update
      apt-get install -y python3 python3-venv python3-pip ufw

      # Se existir serviço Node antigo, desabilite
      systemctl disable --now node-app.service 2>/dev/null || true
      rm -f /etc/systemd/system/node-app.service || true

      # venv da API
      install -d -m 0755 /opt/venvs/api
      if [ ! -f /opt/venvs/api/bin/activate ]; then
        python3 -m venv /opt/venvs/api
      fi
      /opt/venvs/api/bin/pip install --upgrade pip

      # Dependências da API (usar PyMySQL para evitar libs nativas)
      if [ -f /srv/app/requirements.txt ]; then
        /opt/venvs/api/bin/pip install -r /srv/app/requirements.txt
      else
        /opt/venvs/api/bin/pip install fastapi "uvicorn[standard]" sqlalchemy pymysql "python-jose[cryptography]" "passlib[bcrypt]"
      fi

      # hosts internos
      grep -q "192.168.90.30 database" /etc/hosts || echo "192.168.90.30 database" >> /etc/hosts

      # API mínima se faltar
      if [ ! -f /srv/app/main.py ]; then
        cat >/srv/app/main.py <<'PY'
from fastapi import FastAPI
app = FastAPI(title="Tuesday API")
@app.get("/health")
def health(): return {"status":"ok","service":"api"}
PY
      fi

      # Service FastAPI (porta 8001)
      cat >/etc/systemd/system/fastapi-api.service <<'EOF'
[Unit]
Description=Tuesday FastAPI API
After=network-online.target
Wants=network-online.target

[Service]
User=vagrant
WorkingDirectory=/srv/app
Environment="PATH=/opt/venvs/api/bin"
Environment="DB_HOST=database"
Environment="DB_USER=app_user"
Environment="DB_PASS=app_pass"
Environment="DB_NAME=app_db"
ExecStart=/opt/venvs/api/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=3
KillMode=process

[Install]
WantedBy=multi-user.target
EOF

      systemctl daemon-reload
      systemctl enable fastapi-api.service
      systemctl restart fastapi-api.service || true

      # Firewall interno
      ufw --force reset
      ufw default deny incoming
      ufw default allow outgoing
      ufw allow 22/tcp
      ufw allow 8001/tcp
      ufw --force enable
    SHELL
  end

  # ===================== DATABASE (MySQL interno) =====================
  config.vm.define "database" do |db|
    db.vm.hostname = "database"

    # Host-only interna
    db.vm.network "private_network",
      ip: "192.168.90.30", netmask: "255.255.255.0", vmware__netname: "vmnet3"

    # (Opcional: debug do host) Port-forward 13306 -> 3306
    db.vm.network "forwarded_port", guest: 3306, host: 13306, auto_correct: true

    db.vm.synced_folder "./database", "/srv/database", create: true,
      owner: "vagrant", group: "vagrant"

    db.vm.provider "vmware_desktop" do |v|
      v.gui = true
      v.memory = "1536"
      v.cpus = 1
      v.vmx["displayName"] = "DB - MySQL"
    end

    db.vm.provision "shell", inline: <<-'SHELL'
      set -eux
      export DEBIAN_FRONTEND=noninteractive

      apt-get update
      apt-get install -y mysql-server ufw

      mysql -uroot -e "CREATE DATABASE IF NOT EXISTS app_db;"
      mysql -uroot -e "CREATE USER IF NOT EXISTS 'app_user'@'%' IDENTIFIED BY 'app_pass';"
      mysql -uroot -e "GRANT ALL PRIVILEGES ON app_db.* TO 'app_user'@'%'; FLUSH PRIVILEGES;"

      CFG="/etc/mysql/mysql.conf.d/mysqld.cnf"
      if grep -q "^bind-address" "$CFG"; then
        sed -i 's/^bind-address.*/bind-address = 192.168.90.30/' "$CFG"
      else
        echo "bind-address = 192.168.90.30" >> "$CFG"
      fi
      systemctl restart mysql

      # Firewall
      ufw --force reset
      ufw default deny incoming
      ufw default allow outgoing
      ufw allow 22/tcp
      ufw allow 3306/tcp
      ufw --force enable
    SHELL
  end
end
