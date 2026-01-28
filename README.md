# 🚀 Deploy Manager Platform

Deploy Manager é uma plataforma web interna baseada em Django para execução controlada de scripts de deploy, monitoramento de infraestrutura e gestão de segredos (secrets) em servidores Linux.

A plataforma cria uma camada profissional entre o operador e o servidor, substituindo acessos manuais via SSH por uma interface web segura, auditável e controlada.

---

## 🎯 Objetivos da Plataforma

- Padronizar execuções de deploy
- Reduzir acesso direto via SSH
- Criar auditoria de operações
- Centralizar execução de scripts
- Monitorar saúde do servidor
- Gerenciar secrets de forma controlada

---

## 🧱 Arquitetura Geral

👤 Usuário (Browser)
        |
        v
🌐 NGINX (HTTPS)
        |
        v
🧩 Gunicorn (www-data)
        |
        v
🐍 Django (Deploy Manager)
        |
        v
🔐 sudo controlado
        |
        v
📜 Scripts em /opt/deploy/*.sh

---

## 🧩 Componentes

- 🐍 Django (backend + frontend)
- 🧩 Gunicorn (WSGI server)
- 🌐 NGINX (reverse proxy + SSL)
- ⚙️ systemd (gerenciamento do serviço)
- 🔐 sudoers (execução controlada)
- 📊 psutil (métricas de servidor)

---

## 📁 Estrutura de Diretórios

### Aplicação

/opt/deploy_manager/
  ├── core/                  
  ├── deploy/                
  ├── venv/                  
  ├── manage.py

### Scripts de Deploy

/opt/deploy/
  ├── deploy_eduflow.sh
  ├── deploy_ptecia.sh
  ├── deploy_certificados.sh
  └── ...

Função:
- Scripts reais de deploy
- Executados como root via sudo controlado
- Chamados pela plataforma web

### Secrets / Variáveis de Ambiente

/opt/secret/
  ├── eduflow.env
  ├── ptecia.env
  ├── certificados.env
  └── ...

Função:
- Tokens
- Senhas
- Variáveis de ambiente
- Configurações sensíveis
- Editáveis pela interface web

---

## 🔐 Segurança e Privilégios

A aplicação NÃO roda como root.

Gunicorn roda como:

User: www-data  
Group: www-data

Execução privilegiada é feita via sudoers controlado.

---

## 🛡️ Sudoers (Execução Controlada)

Arquivo:

/etc/sudoers.d/deploy-manager

Conteúdo:

www-data ALL=(root) NOPASSWD: /opt/deploy/*.sh  
www-data ALL=(root) NOPASSWD: /usr/bin/ping

Permite:
- Executar SOMENTE scripts em /opt/deploy
- Executar ping para healthcheck
- Nada além disso

---

## 🔑 Permissões de Diretórios

### Scripts

chown root:root /opt/deploy/*.sh  
chmod 750 /opt/deploy/*.sh

### Secrets (grupo dedicado)

groupadd ops  
usermod -aG ops www-data  

chown -R root:ops /opt/secret  
chmod -R 770 /opt/secret

---

## 🔄 Fluxo de Execução de Scripts

1. Usuário clica em "Executar"
2. Django chama subprocess com sudo
3. Script é executado como root
4. STDOUT/STDERR enviados em tempo real (SSE)
5. Logs salvos no banco
6. Status atualizado (success/error/timeout)

Execução:

/usr/bin/sudo /opt/deploy/SEU_SCRIPT.sh

---

## 📊 Health & Métricas

- CPU (%)
- Memória (%)
- Disco (%)
- Ping externo (latência)

---

## ⚙️ systemd (Serviço)

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
RestartSec=5

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

## 🧠 Django Settings Importantes

DEBUG = False

ALLOWED_HOSTS = deploy-manager.pdinfinita.com

STATIC_ROOT = /var/www/deploy-manager/static/

LOGIN_URL = /accounts/login/  
LOGIN_REDIRECT_URL = /  
LOGOUT_REDIRECT_URL = /accounts/login/

---

## 📦 Static Files

python manage.py collectstatic  
chown -R www-data:www-data /var/www/deploy-manager

---

## 🪵 Logs & Troubleshooting

journalctl -u deploy-manager -f  
tail -f /var/log/nginx/deploy-manager.error.log

---

## ❌ Erros Comuns

sudo: No such file or directory  
→ Use /usr/bin/sudo no código e no PATH do systemd

Permission denied em /opt/secret  
→ Grupo ops + chmod 770

Script não executa  
→ Teste: sudo -u www-data /usr/bin/sudo /opt/deploy/SEU_SCRIPT.sh

---

## 🧭 Pontos de Melhoria e Evolução da Plataforma

Segurança Avançada  
Governança de Deploy  
RBAC (viewer/operator/admin)  
Observabilidade (Prometheus, SLA)  
Integração CI/CD  
Auditoria e Compliance  
Multi-Host  
UX e Produto  
Hardening  
Posicionamento como plataforma corporativa

---

## ⚠️ Aviso de Segurança

Esta plataforma executa scripts como root via sudo controlado.  
Use apenas em ambientes internos e controlados.

Audite regularmente:
- sudoers
- permissões
- usuários
- scripts

---

## 🏢 Autor / Plataforma

Deploy Manager Platform  
Infra & DevOps Automation  
PD Infinita
