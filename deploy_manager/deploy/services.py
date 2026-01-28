############################################
# FILE: deploy/services.py
############################################
import os
from django.utils import timezone
from .models import DeployScript

# Configure aqui o local dos seus scripts
DEPLOY_DIR = "/opt/deploy"


def sync_scripts_from_disk():
    """
    Sincroniza os arquivos .sh do disco com o Banco de Dados.
    Cria novos registros e remove scripts que não existem mais no disco.
    """
    # 1. Pega todos os arquivos .sh do disco
    files_on_disk = set()
    if os.path.exists(DEPLOY_DIR):
        for fname in os.listdir(DEPLOY_DIR):
            if fname.startswith("deploy_") and fname.endswith(".sh"):
                full_path = os.path.join(DEPLOY_DIR, fname)
                files_on_disk.add(full_path)
                
                # Cria ou atualiza o script no banco
                DeployScript.objects.update_or_create(
                    script_path=full_path,
                    defaults={
                        "name": fname.replace("deploy_", "").replace(".sh", "").replace("_", " ").title()
                    }
                )

    # 2. Remove do banco os scripts que não foram encontrados no disco
    # (Isso limpa cards de scripts que você apagou ou moveu)
    scripts_in_db = DeployScript.objects.all()
    for script in scripts_in_db:
        if script.script_path not in files_on_disk:
            script.delete()


def run_deploy_script(script: DeployScript, user):
    """
    Executa o script usando sudo e atualiza o modelo com o resultado.
    """
    try:
        import subprocess
        
        # Executa o script. Capture_output pega stdout e stderr.
        # Timeout de 30 minutos (1800s)
        result = subprocess.run(
            ["sudo", script.script_path],
            capture_output=True,
            text=True,
            timeout=1800
        )

        # Define o status
        status = "success" if result.returncode == 0 else "error"
        
        # Atualiza o objeto
        script.last_status = status
        script.last_run_at = timezone.now()
        script.last_run_by = user
        
        # Salva os logs (limitados aos últimos 10000 caracteres para não explodir o banco)
        script.last_stdout = result.stdout[-10000:] if result.stdout else ""
        script.last_stderr = result.stderr[-10000:] if result.stderr else ""
        
        script.save()

        return result.returncode, script.last_stdout, script.last_stderr

    except subprocess.TimeoutExpired:
        script.last_status = "timeout"
        script.last_run_at = timezone.now()
        script.last_run_by = user
        script.last_stdout = "TIMEOUT: O script excedeu o tempo limite de execução."
        script.last_stderr = ""
        script.save()
        return 1, script.last_stdout, "Erro de Timeout"

    except Exception as e:
        script.last_status = "exception"
        script.last_run_at = timezone.now()
        script.last_run_by = user
        script.last_stdout = ""
        script.last_stderr = str(e)
        script.save()
        return 1, "", str(e)