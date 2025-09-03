Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-22.04"

  # ---------- FRONTEND (FastAPI) ----------
  config.vm.define "frontend" do |fe|
    fe.vm.hostname = "frontend"

    # NIC externa (vmnet4) + interna (vmnet5)
    fe.vm.network "private_network",
      ip: "192.168.40.10", netmask: "255.255.255.0", vmware__netname: "vmnet4"
    fe.vm.network "private_network",
      ip: "192.168.90.10", netmask: "255.255.255.0", vmware__netname: "vmnet5"

    # Pasta sincronizada
    fe.vm.synced_folder "./frontend", "/srv/frontend",
      create: true,
      owner: "vagrant", group: "vagrant" # pode ser ignorado pelo VMware, mas não quebra
      # mount_options: ["uid=1000","gid=1000","umask=022"] # opcional; pode não ter efeito no VMware

    fe.vm.provider "vmware_desktop" do |v|
      v.gui = true
      v.memory = "2048"
      v.cpus = 2
      v.vmx["displayName"] = "FE - FastAPI Frontend"
    end

    fe.vm.provision "shell", inline: <<-'SHELL'
      set -eux
      export DEBIAN_FRONTEND=noninteractive
      apt-get update
      apt-get install -y python3 python3-venv python3-pip python3-dev \
                         default-libmysqlclient-dev build-essential curl git ufw

      # >>> venv FORA da pasta sincronizada (evita problemas de permissão no hgfs)
      install -d -m 0755 /opt/venvs/frontend
      python3 -m venv /opt/venvs/frontend
      /opt/venvs/frontend/bin/pip install --upgrade pip
      if [ -f /srv/frontend/requirements.txt ]; then
        /opt/venvs/frontend/bin/pip install -r /srv/frontend/requirements.txt
      else
        /opt/venvs/frontend/bin/pip install fastapi "uvicorn[standard]" mysqlclient httpx
      fi

      # Resoluções internas
      grep -q "192.168.90.20 app" /etc/hosts || echo "192.168.90.20 app" >> /etc/hosts
      grep -q "192.168.90.30 database" /etc/hosts || echo "192.168.90.30 database" >> /etc/hosts

      # Service systemd (trabalha na pasta sincronizada, usa venv em /opt/venvs/frontend)
      cat >/etc/systemd/system/fastapi-frontend.service <<'EOF'
      [Unit]
      Description=FastAPI Frontend
      After=network.target

      [Service]
      User=vagrant
      WorkingDirectory=/srv/frontend
      Environment="PATH=/opt/venvs/frontend/bin"
      Environment="APP_URL=http://app:3000"
      ExecStart=/opt/venvs/frontend/bin/uvicorn main:app --host 0.0.0.0 --port 8000
      Restart=always

      [Install]
      WantedBy=multi-user.target
      EOF

      systemctl daemon-reload
      systemctl enable fastapi-frontend.service
      systemctl start fastapi-frontend.service || true

      ufw --force reset
      ufw allow 8000/tcp
      ufw --force enable
    SHELL
  end

  # ---------- APP (Node.js) ----------
  config.vm.define "app" do |app|
    app.vm.hostname = "app"

    # Apenas rede interna
    app.vm.network "private_network",
      ip: "192.168.90.20", netmask: "255.255.255.0", vmware__netname: "vmnet5"

    # Pasta sincronizada (evite chown/chmod)
    app.vm.synced_folder "./app", "/srv/app",
      create: true,
      owner: "vagrant", group: "vagrant"

    app.vm.provider "vmware_desktop" do |v|
      v.gui = true
      v.memory = "2048"
      v.cpus = 2
      v.vmx["displayName"] = "APP - Node.js"
    end

    app.vm.provision "shell", inline: <<-'SHELL'
      set -eux
      apt-get update
      apt-get install -y curl git ufw jq

      # Node 20 LTS
      curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
      apt-get install -y nodejs

      cd /srv/app || exit 0
      if [ -f package.json ]; then
        npm ci || npm install
      fi

      grep -q "192.168.90.30 database" /etc/hosts || echo "192.168.90.30 database" >> /etc/hosts

      cat >/etc/systemd/system/node-app.service <<'EOF'
      [Unit]
      Description=Node App
      After=network.target

      [Service]
      User=vagrant
      WorkingDirectory=/srv/app
      ExecStart=/bin/bash -lc 'if [ -f package.json ] && jq -e ".scripts.start" package.json >/dev/null 2>&1; then npm run start; elif [ -f server.js ]; then node server.js; elif [ -f index.js ]; then node index.js; else sleep 10; fi'
      Restart=always
      Environment=NODE_ENV=production

      [Install]
      WantedBy=multi-user.target
      EOF

      systemctl daemon-reload
      systemctl enable node-app.service
      systemctl start node-app.service || true

      ufw --force reset
      ufw allow 3000/tcp
      ufw --force enable
    SHELL
  end

  # ---------- DATABASE (MySQL) ----------
  config.vm.define "database" do |db|
    db.vm.hostname = "database"

    # Apenas rede interna
    db.vm.network "private_network",
      ip: "192.168.90.30", netmask: "255.255.255.0", vmware__netname: "vmnet5"

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

      ufw --force reset
      ufw allow 3306/tcp
      ufw --force enable
    SHELL
  end
end
