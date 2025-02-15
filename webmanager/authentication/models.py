import random
import uuid
from datetime import timedelta
from django.db import models
from django.utils.timezone import now, make_aware
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

class OtpCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        """Verifica se o OTP ainda é válido (até 15 minutos) considerando o timezone configurado"""
        current_time = now()
        if settings.USE_TZ and self.created_at.tzinfo is None:
            from django.utils.timezone import make_aware
            self.created_at = make_aware(self.created_at)
        return current_time - self.created_at <= timedelta(minutes=15) and not self.is_used

    def mark_as_used(self):
        """Marca o código como utilizado"""
        self.is_used = True
        self.save()

    @staticmethod
    def generate_otp():
        """Gera um código OTP aleatório de 6 dígitos"""
        return ''.join(random.choices("0123456789", k=6))


class ResetPasswordToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        """Verifica se o token ainda é válido (até 15 minutos)"""
        return now() - self.created_at <= timedelta(minutes=15)