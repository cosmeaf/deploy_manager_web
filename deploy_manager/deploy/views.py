############################################
# FILE: deploy/views.py
############################################
import subprocess
import psutil
import socket
import os
import logging
import re
import time
import signal
import select
from datetime import datetime

from django.shortcuts import render, get_object_or_404, redirect
from django.http import StreamingHttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.conf import settings

from .models import DeployScript
from .services import sync_scripts_from_disk

logger = logging.getLogger(__name__)

# --- Configurações ---
SECRET_DIR = getattr(settings, "DEPLOY_SECRET_DIR", "/opt/secret/")
SCRIPT_TIMEOUT = 300  # Timeout em segundos
ALLOWED_SECRET_EXTENSIONS = {'.env', '.conf', '.ini', '.txt', '.yaml', '.yml', '.json'}

# Regex para remover códigos de cor ANSI
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# ==========================================
# 1. DASHBOARD HOME (Gráficos e Métricas)
# ==========================================

@login_required
def dashboard_home(request):
    # --- Deploy Stats ---
    total_scripts = DeployScript.objects.count()
    success_count = DeployScript.objects.filter(last_status='success').count()
    error_count = DeployScript.objects.filter(last_status='error').count()
    last_deploy = DeployScript.objects.filter(last_run_at__isnull=False).order_by('-last_run_at').first()

    # --- Server Metrics ---
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
    except Exception:
        cpu_percent = 0
        
    try:
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        mem_percent = mem.percent
        disk_percent = disk.percent
    except Exception:
        mem_percent = disk_percent = 0

    # --- Network Info ---
    hostname = socket.gethostname()
    
    # Tentativa robusta de pegar o IP principal
    server_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        server_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    # --- Ping / Latency ---
    latency_ms = None
    network_status = "unknown"
    try:
        ping_output = subprocess.check_output(
            ["/usr/bin/ping", "-c", "1", "8.8.8.8"], 
            timeout=2, stderr=subprocess.DEVNULL
        ).decode()
        
        match = re.search(r"time=(?P<time>[0-9\.]+)", ping_output)
        if match:
            latency_ms = match.group('time')
            network_status = "online"
    except subprocess.TimeoutExpired:
        network_status = "timeout"
    except Exception:
        network_status = "offline"

    context = {
        'total_scripts': total_scripts,
        'success_count': success_count,
        'error_count': error_count,
        'last_deploy': last_deploy,
        'cpu_percent': cpu_percent,
        'mem_percent': mem_percent,
        'disk_percent': disk_percent,
        'hostname': hostname,
        'server_ip': server_ip,
        'latency_ms': latency_ms,
        'network_status': network_status,
    }

    return render(request, 'deploy/home.html', context)

# ==========================================
# 2. DASHBOARD DEPLOYS (Lista de Scripts)
# ==========================================
@login_required
def dashboard(request):
    try:
        sync_scripts_from_disk()
    except Exception as e:
        logger.error(f"Erro ao sincronizar scripts: {e}")
        
    scripts = DeployScript.objects.all().order_by("name")
    return render(request, "deploy/dashboard.html", {"scripts": scripts})

# ==========================================
# 3. EXECUÇÃO DE SCRIPTS
# ==========================================
@login_required
def run_script(request, script_id):
    script = get_object_or_404(DeployScript, id=script_id)
    return render(request, "deploy/partials/_row.html", {"script": script})


@login_required
def stream_script(request, script_id):
    script = get_object_or_404(DeployScript, id=script_id)
    
    def remove_ansi(text):
        return ANSI_ESCAPE.sub('', text)

    def generate():
        process = None
        full_output = []
        full_stderr = []
        start_time = time.time()
        
        try:
            process = subprocess.Popen(
                ["/usr/bin/sudo", script.script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                preexec_fn=os.setsid 
            )
            
            while True:
                if time.time() - start_time > SCRIPT_TIMEOUT:
                    raise subprocess.TimeoutExpired(script.script_path, SCRIPT_TIMEOUT)

                if process.poll() is not None:
                    remaining_out = process.stdout.read()
                    remaining_err = process.stderr.read()
                    if remaining_out:
                        clean_line = remove_ansi(remaining_out).replace('\r', '\n')
                        full_output.append(clean_line)
                        yield f"data: {clean_line}\n\n"
                    if remaining_err:
                        clean_err = remove_ansi(remaining_err).replace('\r', '\n')
                        full_stderr.append(clean_err)
                        yield f"data: [STDERR] {clean_err}\n\n"
                    break

                # Non-blocking read
                ready, _, _ = select.select([process.stdout, process.stderr], [], [], 0.1)
                
                for stream in ready:
                    if stream == process.stdout:
                        line = stream.readline()
                        if line:
                            line = remove_ansi(line).replace('\r', '\n')
                            full_output.append(line)
                            yield f"data: {line}\n\n"
                    
                    elif stream == process.stderr:
                        err_line = stream.readline()
                        if err_line:
                            err_line = remove_ansi(err_line).replace('\r', '\n')
                            full_stderr.append(err_line)
                            yield f"data: [STDERR] {err_line}\n\n"

            returncode = process.returncode
            status = "success" if returncode == 0 else "error"
            
            script.last_status = status
            script.last_run_at = timezone.now()
            script.last_run_by = request.user
            script.last_stdout = "".join(full_output)[-10000:] 
            script.last_stderr = "".join(full_stderr)[-10000:]
            script.save()
            
            yield f"data: [FIM_DA_EXECUCAO] Status: {status}\n\n"
        
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout na execução do script {script.id}")
            if process:
                try: os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                except: pass
            script.last_status = "timeout"
            script.save()
            yield f"data: [TIMEOUT] Execução excedeu {SCRIPT_TIMEOUT}s\n\n"
        
        except Exception as e:
            logger.error(f"Erro na stream_script: {str(e)}", exc_info=True)
            if process:
                try: os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                except: pass
            yield f"data: [ERRO INTERNO]: {str(e)}\n\n"
    
    response = StreamingHttpResponse(generate(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response

# ==========================================
# 4. EDITOR DE SECRETS
# ==========================================
@login_required
def list_secrets(request):
    if not os.path.exists(SECRET_DIR):
        return render(request, 'deploy/secrets/list.html', {
            'error': f'Diretório {SECRET_DIR} não encontrado ou o servidor não tem permissão de acesso.'
        })
    
    files = []
    try:
        for f in os.listdir(SECRET_DIR):
            path = os.path.join(SECRET_DIR, f)
            if os.path.isfile(path) and not f.startswith('.'):
                stat = os.stat(path)
                modified_dt = timezone.make_aware(datetime.fromtimestamp(stat.st_mtime))
                
                files.append({
                    'name': f,
                    'size': stat.st_size,
                    'modified': modified_dt,
                    'ext': os.path.splitext(f)[1].lower()
                })
        files.sort(key=lambda x: x['name'])
    except PermissionError:
        logger.error(f"Permissão negada ao ler {SECRET_DIR}")
        return render(request, 'deploy/secrets/list.html', {'error': 'Sem permissão para ler o diretório de secrets.'})
    except Exception as e:
        logger.error(f"Erro ao listar secrets: {e}")
        return render(request, 'deploy/secrets/list.html', {'error': str(e)})
    
    return render(request, 'deploy/secrets/list.html', {'files': files})

@login_required
def edit_secret(request, filename):
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(SECRET_DIR, safe_filename)
    file_ext = os.path.splitext(safe_filename)[1].lower()
    
    if file_ext not in ALLOWED_SECRET_EXTENSIONS:
        return render(request, 'deploy/error.html', {
            'message': f'Edição não permitida para arquivos do tipo "{file_ext}".'
        })
    
    if not os.path.exists(file_path):
        return render(request, 'deploy/error.html', {'message': 'Arquivo não encontrado.'})
    
    if request.method == 'GET':
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            return render(request, 'deploy/secrets/edit.html', {
                'filename': safe_filename, 
                'content': content
            })
        except Exception as e:
            return render(request, 'deploy/secrets/edit.html', {
                'filename': safe_filename, 
                'content': '', 
                'error': f'Erro ao ler arquivo: {str(e)}'
            })
    
    elif request.method == 'POST':
        new_content = request.POST.get('content', '')
        try:
            with open(file_path, 'w') as f:
                f.write(new_content)
            return redirect('list_secrets')
        except Exception as e:
            return render(request, 'deploy/secrets/edit.html', {
                'filename': safe_filename, 
                'content': new_content, 
                'error': f'Erro ao salvar arquivo: {str(e)}'
            })

# ==========================================
# 5. HEALTH CHECK
# ==========================================
def health_check(request):
    return render(request, 'deploy/health.html', {'status': 'OK'})