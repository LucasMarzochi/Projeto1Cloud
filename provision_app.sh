#!/usr/bin/env bash
set -eux

APP_VENV="/opt/venvs/api"
VAGRANT_HOME="/home/vagrant"

# checa se o venv do app existe se no cria 
if [ ! -d "$APP_VENV" ]; then
  python3 -m venv "$APP_VENV"
fi

"$APP_VENV/bin/pip" install --upgrade pip

cd /vagrant

# instala os requirements do app e front end no venv
"$APP_VENV/bin/pip" install -r app/requirements.txt
"$APP_VENV/bin/pip" install -r frontend/requirements.txt

# instala as dependencias dos testes, unit e integration, no venv
"$APP_VENV/bin/pip" install pytest pytest-cov httpx sqlalchemy pymysql

echo "[provision_app] Dependências e pytest instalados no venv ${APP_VENV}"

BASHRC="${VAGRANT_HOME}/.bashrc"
MARKER="# >>> Tuesday Project1Cloud test env >>>"

# faz a configuracao do .bashrc apenas 1 vez
if ! grep -q "$MARKER" "$BASHRC"; then
  cat <<EOF >> "$BASHRC"

${MARKER}
# ativa o venv da api atomaticamente
if [ -d "${APP_VENV}" ]; then
  source "${APP_VENV}/bin/activate"
fi

# configura as variaveis do ambiente
export DB_HOSTS="database,192.168.90.30"
export DB_USER="app_user"
export DB_PASS="app_pass"
export DB_NAME="app_db"
export DB_PORT=3306
export JWT_SECRET="change-me"
export JWT_EXPIRES_MIN=60
# <<< Tuesday Project1Cloud test env <<<
EOF
fi

chown vagrant:vagrant "$BASHRC"

echo "[provision_app] Ambiente de testes configurado no .bashrc do vagrant"
