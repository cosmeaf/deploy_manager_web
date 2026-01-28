############################################
# FILE: deploy/models.py
############################################
from django.db import models
from django.contrib.auth.models import User


class DeployScript(models.Model):
    name = models.CharField(max_length=200)
    script_path = models.CharField(max_length=500, unique=True)
    
    # Status da última execução
    last_status = models.CharField(max_length=20, blank=True, null=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_run_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    
    # Logs da execução (Armazenados no DB para persistência)
    last_stdout = models.TextField(blank=True, null=True)
    last_stderr = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']