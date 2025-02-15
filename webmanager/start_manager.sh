#!/bin/bash

APP_DIR="$(dirname "$(realpath "$0")")"
LOG_DIR="$APP_DIR/logs"
LOG_FILE="$LOG_DIR/manager.log"
DJANGO_PORT=7000
CELERY_WORKER="celery -A core worker --loglevel=info --detach"
CELERY_BEAT="celery -A core beat --loglevel=info --detach"

# Criar diretórios necessários se não existirem
mkdir -p "$LOG_DIR"

start() {
    echo "Iniciando Django e Celery..."
    cd $APP_DIR || { echo "Erro: Falha ao acessar $APP_DIR"; exit 1; }
    
    # Inicia Django
    if pgrep -f "manage.py runserver" > /dev/null; then
        echo "Django já está rodando."
    else
        nohup python3 manage.py runserver 0.0.0.0:$DJANGO_PORT > "$LOG_FILE" 2>&1 &
        echo "Django iniciado na porta $DJANGO_PORT."
    fi
    
    # Inicia Celery Worker
    if pgrep -f "celery worker" > /dev/null; then
        echo "Celery Worker já está rodando."
    else
        $CELERY_WORKER
        echo "Celery Worker iniciado."
    fi
    
    # Inicia Celery Beat
    if pgrep -f "celery beat" > /dev/null; then
        echo "Celery Beat já está rodando."
    else
        $CELERY_BEAT
        echo "Celery Beat iniciado."
    fi
}

stop() {
    echo "Parando Django e Celery..."
    pkill -f "manage.py runserver" && echo "Django parado." || echo "Django não estava rodando."
    pkill -f "celery worker" && echo "Celery Worker parado." || echo "Celery Worker não estava rodando."
    pkill -f "celery beat" && echo "Celery Beat parado." || echo "Celery Beat não estava rodando."
}

restart() {
    echo "Reiniciando Django e Celery..."
    stop
    sleep 2
    start
}

status() {
    echo "Status dos serviços:"
    pgrep -f "manage.py runserver" > /dev/null && echo "Django: Rodando" || echo "Django: Parado"
    pgrep -f "celery worker" > /dev/null && echo "Celery Worker: Rodando" || echo "Celery Worker: Parado"
    pgrep -f "celery beat" > /dev/null && echo "Celery Beat: Rodando" || echo "Celery Beat: Parado"
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    *)
        echo "Uso: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
