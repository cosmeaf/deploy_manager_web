# README - Certificados API (Projeto Desenvolve)
Deploy com Gunicorn + NGINX + SSL + systemd + .env (python-decouple)
Dominio: https://certificados-api.pdinfinita.com
Servidor: 147.79.86.247

================================================================================
1) VISÃO GERAL
================================================================================

Este documento descreve o passo a passo completo do deploy da API "certificados-api",
incluindo:

- Subdomínios e DNS
- Gunicorn rodando como serviço systemd
- NGINX como reverse proxy com SSL (Let's Encrypt)
- Swagger/Docs como primeira página (/)
- Configuração via .env com python-decouple
- Media e Static servidos pelo NGINX via /var/www/<app>/
- Correções aplicadas (DisallowedHost/HTTP_HOST, root 400, .env não sendo lido)

Estrutura final:
- Código: /opt/projetodesenvolve_api
- Venv:  /opt/projetodesenvolve_api/venv
- Static: /var/www/certificados-api/static
- Media:  /var/www/certificados-api/media
- NGINX site: /etc/nginx/sites-available/certificados-api.conf
- systemd: /etc/systemd/system/certificados-api.service

================================================================================
2) DNS / SUBDOMÍNIOS (Cloudflare)
================================================================================

Foram criados registros A "DNS only" apontando para o IP do servidor:

- certificados.pdinfinita.com      -> 147.79.86.247   (DNS only)
- certificados-api.pdinfinita.com  -> 147.79.86.247   (DNS only)

Observação:
- O backend desta API utiliza: certificados-api.pdinfinita.com
- O frontend pode usar: certificados.pdinfinita.com (se existir frontend)

================================================================================
3) GUNICORN (EXECUÇÃO LOCAL - TESTE)
================================================================================

Dentro do path do projeto:

cd /opt/projetodesenvolve_api

Com venv ativada:

source /opt/projetodesenvolve_api/venv/bin/activate

Comando de teste usado para subir a aplicação manualmente:

gunicorn projetodesenvolve_api.wsgi:application \
  --bind 0.0.0.0:5799 \
  --workers 4 \
  --timeout 600 \
  --log-level debug \
  --access-logfile - \
  --error-logfile -

Validação local (antes do NGINX):

curl -I http://127.0.0.1:5799/

================================================================================
4) PROBLEMAS IDENTIFICADOS E CORRIGIDOS
================================================================================

4.1) DisallowedHost / Invalid HTTP_HOST header
----------------------------------------------
Sintoma:
- DisallowedHost at /
- Invalid HTTP_HOST header: 'certificados-api.pdinfinita.com'
- Respostas 400 no acesso via domínio.

Causa:
- ALLOWED_HOSTS não continha o domínio.
- O arquivo .env não estava sendo lido porque python-decouple não estava instalado
  e/ou o settings não estava carregando variáveis corretamente.

Correção:
- Instalação do python-decouple
- Ajuste do settings.py para ler variáveis via config(...)
- Definição correta de DJANGO_ALLOWED_HOSTS contendo:
  certificados-api.pdinfinita.com e certificados.pdinfinita.com

4.2) Root (/) retornando 400 ao abrir no browser
------------------------------------------------
Sintoma:
- "GET / HTTP/1.0" 400 ... ao acessar https://certificados-api.pdinfinita.com/

Causa:
- A API não tinha rota explícita para a raiz (/).
- Browser acessa / e /favicon.ico, gerando ruído.

Correção:
- Root "/" foi configurada para abrir o Swagger/Docs.
- Após isso, logs passaram a mostrar 200 (OK).

4.3) Warning do drf_yasg / pkg_resources deprecated
---------------------------------------------------
Sintoma:
- UserWarning: pkg_resources is deprecated... slated for removal

Causa:
- drf_yasg importa pkg_resources (deprecated no Python 3.12).

Correção operacional (curto prazo):
- A aplicação continua funcionando. É warning, não erro.
- Para manter logs limpos em produção, definimos:
  PYTHONWARNINGS="ignore:pkg_resources is deprecated"
  dentro do service systemd.

Correção recomendada (médio prazo):
- Migrar drf_yasg -> drf-spectacular para eliminar o warning na raiz.

================================================================================
5) DEPENDÊNCIAS INSTALADAS
================================================================================

Dentro da venv, foi instalado:

- python-decouple

Comando:

pip install python-decouple

(opcional) Também foi avaliado pin de setuptools (<81) para compatibilidade,
mas o warning do drf_yasg não some, pois o import é feito pelo próprio pacote.

================================================================================
6) CONFIGURAÇÃO VIA .env
================================================================================

Arquivo .env no path base do projeto:

/opt/projetodesenvolve_api/.env

Exemplo de variáveis utilizadas:

DJANGO_SECRET_KEY=...
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,147.79.86.247,certificados.pdinfinita.com,certificados-api.pdinfinita.com

CSRF_TRUSTED_ORIGINS=https://certificados.pdinfinita.com,https://certificados-api.pdinfinita.com

CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://certificados.pdinfinita.com

DJANGO_MEDIA_ROOT=/var/www/certificados-api/media
DJANGO_MEDIA_URL=/media/
DJANGO_STATIC_ROOT=/var/www/certificados-api/static
DJANGO_STATIC_URL=/static/

Permissões recomendadas do .env:

chmod 600 /opt/projetodesenvolve_api/.env

================================================================================
7) ALTERAÇÕES NO settings.py (RESUMO)
================================================================================

Foram ajustados pontos essenciais:

- Leitura de SECRET_KEY, DEBUG, ALLOWED_HOSTS via python-decouple
- Ajuste de STATIC_ROOT e MEDIA_ROOT para /var/www/certificados-api/
- Reverse proxy:
  SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
  USE_X_FORWARDED_HOST = True
  USE_X_FORWARDED_PORT = True
- CSRF_TRUSTED_ORIGINS via env
- CORS com política de produção (evitar allow all em prod)

Observação:
- CORS_ALLOW_ALL_ORIGINS=True em produção é inseguro. Foi fechado para domínio.

================================================================================
8) URLs: SWAGGER/DOCS NA PRIMEIRA PÁGINA (/)
================================================================================

O urls.py foi ajustado para que a raiz "/" abra o Swagger UI.

Resultado:
- GET / -> 200
- GET /?format=openapi -> 200
- Browser deixa de retornar 400.

================================================================================
9) ESTRUTURA DE STATIC/MEDIA (PADRÃO APP)
================================================================================

Criamos os diretórios específicos da aplicação:

sudo mkdir -p /var/www/certificados-api/static
sudo mkdir -p /var/www/certificados-api/media

Permissões (ajuste conforme user do NGINX):
- Ubuntu/Debian:
  sudo chown -R www-data:www-data /var/www/certificados-api
- RHEL:
  sudo chown -R nginx:nginx /var/www/certificados-api

Permissões gerais:
sudo chmod -R 755 /var/www/certificados-api

Collectstatic (se houver static):
python manage.py collectstatic

================================================================================
10) NGINX - SITE AVAILABLE (certificados-api.conf)
================================================================================

Arquivo:

/etc/nginx/sites-available/certificados-api.conf

Padrão aplicado:
- HTTP 80 redireciona para HTTPS
- HTTPS usa certificados existentes:
  /etc/letsencrypt/live/pdinfinita.com/fullchain.pem
  /etc/letsencrypt/live/pdinfinita.com/privkey.pem
- location /static/ e /media/ via alias em /var/www/certificados-api/
- location / proxypass para Gunicorn em 127.0.0.1:5799

Ativação:

ln -s /etc/nginx/sites-available/certificados-api.conf /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

Validação:
curl -I https://certificados-api.pdinfinita.com/

================================================================================
11) SYSTEMD SERVICE (Gunicorn em produção)
================================================================================

Arquivo:

/etc/systemd/system/certificados-api.service

Objetivo:
- Rodar Gunicorn como serviço
- Restart automático
- Logs via journalctl
- Startup no boot

Comandos de instalação:

systemctl daemon-reexec
systemctl daemon-reload
systemctl enable certificados-api
systemctl start certificados-api
systemctl status certificados-api

Logs:

journalctl -u certificados-api -f

Comandos úteis:

systemctl start certificados-api
systemctl stop certificados-api
systemctl restart certificados-api
systemctl status certificados-api

================================================================================
12) TESTES E VALIDAÇÕES
================================================================================

Testar Gunicorn local (sem NGINX):
curl -I http://127.0.0.1:5799/

Testar via NGINX (domínio):
curl -I https://certificados-api.pdinfinita.com/

Verificar porta:
ss -lntp | grep 5799

Verificar NGINX:
nginx -t
systemctl reload nginx

================================================================================
13) NOTAS DE SEGURANÇA (IMPORTANTES)
================================================================================

- Não versionar .env em git.
- Não colar tokens e segredos em logs/chat.
- Manter CORS fechado em produção.
- Preferir bind do Gunicorn em 127.0.0.1 (com NGINX na frente).
  Exemplo recomendado:
  --bind 127.0.0.1:5799

- Swagger em / é útil, mas em produção pode ser restrito por IP ou auth.

================================================================================
14) PRÓXIMOS MELHORAMENTOS RECOMENDADOS
================================================================================

1) Migrar drf_yasg -> drf-spectacular
   - Remove warning do pkg_resources
   - Geração moderna de OpenAPI

2) Criar endpoint /health/
   - Para monitoramento e uptime checks

3) Rodar serviço com user dedicado (não root)
   - Melhor isolamento e segurança

4) Ajustar NGINX com rate limit e timeouts
   - Proteção contra abuso e uploads maiores, se necessário

================================================================================
FIM
================================================================================
