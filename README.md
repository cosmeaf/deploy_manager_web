# 🚀 Deploy Manager Platform

Deploy Manager é uma plataforma web interna baseada em Django para execução controlada de scripts de deploy, monitoramento de infraestrutura e gestão de segredos (secrets) em servidores Linux.

A plataforma cria uma camada profissional entre o operador e o servidor, substituindo acessos manuais via SSH por uma interface web segura, auditável e controlada.

---

## 🎯 Objetivos

- Padronizar execuções de deploy
- Reduzir acesso direto via SSH
- Criar auditoria de operações
- Centralizar execução de scripts
- Monitorar saúde do servidor
- Gerenciar secrets de forma controlada

---

## 🧱 Arquitetura

Usuário (Browser)
  -> NGINX (HTTPS)
    -> Gunicorn (www-data)
      -> Django (Deploy Manager)
        -> sudo controlado
          -> Scripts em /opt/deploy

---

## 🧩 Componentes

- Django (backend + frontend)
- Gunicorn (WSGI)
- NGINX (reverse proxy + SSL)
- systemd (serviço)
- sudoers (execução controlada)
- psutil (métricas)

---

## 📁 Estrutura de Diretórios

Aplicação:

/opt/deploy_manager/
  core/
  deploy/
  venv/
  manage.py

Scripts de deploy:

/opt/deploy/
  deploy_eduflow.sh
  deploy_ptecia.sh
  deploy_certificados.sh

Secrets:

/opt/secret/
  eduflow.env
  ptecia.env
  certificados.env

---

## 🔐 Modelo de Segurança

- Gunicorn NÃO roda como root
- Usuário: www-data
- Elevação de privilégio via sudoers
- Execução restrita por path

---

## 🛡️ Sudoers

Arquivo:

/etc/sudoers.d/deploy-manager

Conteúdo:

www-data ALL=(root) NOPASSWD: /opt/deploy/*.sh
www-data ALL=(root) NOPASSWD: /usr/bin/ping

---

## 🔑 Permissões

Scripts:

chown root:root /opt/deploy/*.sh
chmod 750 /opt/deploy/*.sh

Secrets:

groupadd ops
usermod -aG ops www-data

chown -R root:ops /opt/secret
chmod -R 770 /opt/secret

---

## 🔄 Fluxo de Execução

1. Usuário clica Executar
2. Django chama subprocess com sudo
3. Script roda como root
4. Output em tempo real (SSE)
5. Logs salvos no banco
6. Status atualizado

Execução real:

/usr/bin/sudo /opt/deploy/SEU_SCRIPT.sh

---

## 📊 Health Check

- CPU (%)
- Memória (%)
- Disco (%)
- Ping externo (latência)

---

## ⚙️ systemd

Arquivo:

/etc/systemd/system/deploy-manager.service

Exemplo:

[Unit]
Description=Deploy Manager Django App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/deploy_manager
Environment="PATH=/opt/deploy_manager/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

ExecStart=/opt/deploy_manager/venv/bin/gunicorn \
  --workers 3 \
  --bind 127.0.0.1:8050 \
  core.wsgi:application

Restart=always

[Install]
WantedBy=multi-user.target

---

## 🌐 NGINX

Arquivo:

/etc/nginx/sites-available/deploy-manager.conf

server {
    listen 80;
    server_name deploy-manager.pdinfinita.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name deploy-manager.pdinfinita.com;

    ssl_certificate /etc/letsencrypt/live/pdinfinita.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pdinfinita.com/privkey.pem;

    location /static/ {
        alias /var/www/deploy-manager/static/;
    }

    location / {
        proxy_pass http://127.0.0.1:8050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

---

## 🧠 Django Settings

DEBUG = False

ALLOWED_HOSTS =
- deploy-manager.pdinfinita.com

STATIC_ROOT = /var/www/deploy-manager/static/

LOGIN_URL = /accounts/login/
LOGIN_REDIRECT_URL = /
LOGOUT_REDIRECT_URL = /accounts/login/

---

## 📦 Static Files

python manage.py collectstatic
chown -R www-data:www-data /var/www/deploy-manager

---

## 🪵 Logs

journalctl -u deploy-manager -f
tail -f /var/log/nginx/deploy-manager.error.log

---

## ❌ Problemas Comuns

sudo not found
→ Use /usr/bin/sudo no código e no systemd PATH

Permission denied em /opt/secret
→ Corrigir grupo ops e chmod

Script não executa
→ Testar:
sudo -u www-data /usr/bin/sudo /opt/deploy/SEU_SCRIPT.sh

---

## 🧭 Evolução da Plataforma

- Usuário dedicado (deploy-runner)
- Aprovação de deploy
- Ambientes (prod/stage/dev)
- RBAC (viewer/operator/admin)
- Prometheus /metrics
- Webhooks GitHub/GitLab
- Auditoria imutável
- Multi-host (agentes)
- Hardening systemd
- MFA no login

---

## ⚠️ Aviso

Esta plataforma executa scripts como root via sudo controlado.
Use apenas em ambientes internos e controlados.

Audite regularmente:
- sudoers
- permissões
- usuários
- scripts

---

## 🏢 Autor

Deploy Manager Platform
Infra & DevOps Automation
Cosme Alves
cosme.alex@gmail.com
PD Infinita
