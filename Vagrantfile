# Vagrantfile — Tuesday.com (Opção 2)
# 3 VMs: frontend (Streamlit), app (FastAPI), database (MySQL)
# Redes:
#   vmnet2 (host-only)   -> 192.168.40.0/24  [frontend exposto]
#   vmnet3 (interna)     -> 192.168.90.0/24  [frontend <-> app <-> db]
# Acesso do host/LAN ao frontend: http://127.0.0.1:18000  (port-forward)
# ou http://ip_do_meu_pc_na_rede:18000

Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-22.04"

  # ---------------- FRONTEND (Streamlit) ----------------
  config.vm.define "frontend" do |fe|
    fe.vm.hostname = "frontend"

    # NICs: host-only (vmnet2) e interna (vmnet3)
    fe.vm.network "private_network",
      ip: "192.168.40.10", netmask: "255.255.255.0", vmware__netname: "vmnet2"
    fe.vm.network "private_network",
      ip: "192.168.90.10", netmask: "255.255.255.0", vmware__netname: "vmnet3"

    # Port-forward para o host / LAN (0.0.0.0)
    fe.vm.network "forwarded_port",
      guest: 8501, host: 18000, host_ip: "0.0.0.0", auto_correct: true

    # Pastas
    fe.vm.synced_folder "./frontend", "/srv/frontend", create: true

    fe.vm.provider "vmware_desktop" do |v|
      v.gui = true
      v.memory = "2048"
      v.cpus   = 2
      v.vmx["displayName"] = "FE - Streamlit"
    end

    fe.vm.provision "shell", inline: <<-'SH'
      set -eux
      export DEBIAN_FRONTEND=noninteractive

      apt-get update
      apt-get install -y python3 python3-venv python3-pip python3-dev \
                         build-essential ufw curl git ca-certificates

      install -d -m 0755 /opt/venvs/frontend
      [ -f /opt/venvs/frontend/bin/activate ] || python3 -m venv /opt/venvs/frontend
      /opt/venvs/frontend/bin/pip install --upgrade pip

      # Exigir arquivos do projeto
      if [ ! -f /srv/frontend/requirements.txt ]; then
        echo "ERROR: /srv/frontend/requirements.txt não encontrado." >&2; exit 1
      fi
      /opt/venvs/frontend/bin/pip install -r /srv/frontend/requirements.txt

      if [ ! -f /srv/frontend/app.py ]; then
        echo "ERROR: /srv/frontend/app.py não encontrado." >&2; exit 1
      fi

      # Hosts internos (para API e DB)
      grep -q "192.168.90.20 app"      /etc/hosts || echo "192.168.90.20 app" >> /etc/hosts
      grep -q "192.168.90.30 database" /etc/hosts || echo "192.168.90.30 database" >> /etc/hosts

      # systemd do Streamlit
      cat >/etc/systemd/system/streamlit-frontend.service <<'EOF'
[Unit]
Description=Tuesday Streamlit Frontend
After=network-online.target
Wants=network-online.target

[Service]
User=vagrant
WorkingDirectory=/srv/frontend
Environment="PATH=/opt/venvs/frontend/bin"
ExecStart=/opt/venvs/frontend/bin/streamlit run /srv/frontend/app.py --server.address=0.0.0.0 --server.port=8501 --server.headless=true
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

      systemctl daemon-reload
      systemctl enable --now streamlit-frontend

      # Firewall: bloquear 90.x para 8501; permitir o resto
      ufw --force reset
      ufw default deny incoming
      ufw default allow outgoing
      ufw allow 22/tcp
      ufw insert 1 deny from 192.168.90.0/24 to any port 8501 proto tcp
      ufw allow 8501/tcp
      ufw --force enable
    SH
  end

  # ---------------- APP (FastAPI) ----------------
  config.vm.define "app" do |app|
    app.vm.hostname = "app"

    app.vm.network "private_network",
      ip: "192.168.90.20", netmask: "255.255.255.0", vmware__netname: "vmnet3"

    app.vm.synced_folder "./app", "/srv/app", create: true

    app.vm.provider "vmware_desktop" do |v|
      v.gui = true
      v.memory = "2048"
      v.cpus   = 2
      v.vmx["displayName"] = "APP - FastAPI"
    end

    app.vm.provision "shell", inline: <<-'SH'
      set -eux
      export DEBIAN_FRONTEND=noninteractive

      apt-get update
      apt-get install -y python3 python3-venv python3-pip python3-dev \
                         build-essential libssl-dev libffi-dev ufw ca-certificates

      install -d -m 0755 /opt/venvs/api
      [ -f /opt/venvs/api/bin/activate ] || python3 -m venv /opt/venvs/api
      /opt/venvs/api/bin/pip install --upgrade pip

      # Exigir arquivos do projeto
      if [ ! -f /srv/app/requirements.txt ]; then
        echo "ERROR: /srv/app/requirements.txt não encontrado." >&2; exit 1
      fi
      /opt/venvs/api/bin/pip install -r /srv/app/requirements.txt

      if [ ! -f /srv/app/main.py ]; then
        echo "ERROR: /srv/app/main.py não encontrado." >&2; exit 1
      fi

      # Hosts internos
      grep -q "192.168.90.30 database" /etc/hosts || echo "192.168.90.30 database" >> /etc/hosts

      # systemd da API
      cat >/etc/systemd/system/fastapi-api.service <<'EOF'
[Unit]
Description=Tuesday FastAPI API
After=network-online.target
Wants=network-online.target

[Service]
User=vagrant
WorkingDirectory=/srv/app
Environment="PATH=/opt/venvs/api/bin"
Environment=DB_HOSTS=database,192.168.90.30
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
      systemctl enable --now fastapi-api

      # Firewall: API somente rede interna 90.x
      ufw --force reset
      ufw default deny incoming
      ufw default allow outgoing
      ufw allow 22/tcp
      ufw allow from 192.168.90.0/24 to any port 8001 proto tcp
      ufw deny  from 192.168.40.0/24 to any port 8001 proto tcp
      ufw deny  from 172.16.21.0/24 to any port 8001 proto tcp || true
      ufw --force enable
    SH
    # liga o provision_app.sh a VM app, para que seja possivel fazer os testes dentro dela também (além de no github)
    app.vm.provision "shell", path: "provision_app.sh"
  end

  # ---------------- DATABASE (MySQL) ----------------
  config.vm.define "database" do |db|
    db.vm.hostname = "database"

    db.vm.network "private_network",
      ip: "192.168.90.30", netmask: "255.255.255.0", vmware__netname: "vmnet3"

    db.vm.synced_folder "./database", "/srv/database", create: true

    db.vm.provider "vmware_desktop" do |v|
      v.gui = true
      v.memory = "1536"
      v.cpus   = 1
      v.vmx["displayName"] = "DB - MySQL"
    end

    db.vm.provision "shell", inline: <<-'SH'
      set -eux
      export DEBIAN_FRONTEND=noninteractive

      apt-get update
      apt-get install -y mysql-server ufw ca-certificates

      CFG="/etc/mysql/mysql.conf.d/mysqld.cnf"
      if grep -q "^bind-address" "$CFG"; then
        sed -i 's/^bind-address.*/bind-address = 192.168.90.30/' "$CFG"
      else
        echo "bind-address = 192.168.90.30" >> "$CFG"
      fi
      systemctl restart mysql

      mysql -e "CREATE DATABASE IF NOT EXISTS app_db;"
      mysql -e "CREATE USER IF NOT EXISTS 'app_user'@'%' IDENTIFIED BY 'app_pass';"
      mysql -e "GRANT ALL PRIVILEGES ON app_db.* TO 'app_user'@'%'; FLUSH PRIVILEGES;"

      if [ -f /srv/database/init.sql ]; then
        mysql app_db < /srv/database/init.sql || true
      fi

      # Firewall: permitir apenas o APP (90.20) em 3306
      ufw --force reset
      ufw default deny incoming
      ufw default allow outgoing
      ufw allow 22/tcp
      ufw allow from 192.168.90.20 to any port 3306 proto tcp
      ufw deny  from 192.168.90.0/24 to any port 3306 proto tcp
      ufw deny  from 192.168.40.0/24 to any port 3306 proto tcp
      ufw deny  from 172.16.21.0/24 to any port 3306 proto tcp || true
      ufw --force enable
    SH
  end
end