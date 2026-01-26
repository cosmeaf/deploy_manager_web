from django.db import models

class CertificadoCSV(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    file_path = models.FilePathField(max_length=500)
    total_lines = models.IntegerField()
    total_certificados = models.IntegerField()
    total_alunos = models.IntegerField()

    def __str__(self):
        return f"CSV de {self.created_at.strftime('%d/%m/%Y %H:%M')} - {self.total_certificados} certs"

    class Meta:
        ordering = ['-created_at']