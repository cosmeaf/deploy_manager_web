from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.contrib.auth import get_user_model, authenticate
from authentication.models import OtpCode, ResetPasswordToken
from django.conf import settings
from services.utils.email_service import EmailService

User = get_user_model()

class UserRegisterSerializer(serializers.ModelSerializer):
    """Serializador para registrar um usuário e retornar tokens JWT"""
    
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    password2 = serializers.CharField(write_only=True, required=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'password', 'password2']

    def validate_email(self, value):
        """Verifica se o email já está cadastrado"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este e-mail já está em uso.")
        return value

    def validate(self, data):
        """Verifica se as senhas são iguais"""
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "As senhas não coincidem."})
        return data

    def create(self, validated_data):
        """Cria o usuário e retorna os tokens JWT"""
        validated_data.pop('password2')  # Removendo o campo antes de criar o usuário
        user = User.objects.create_user(username=validated_data['email'], **validated_data)

        # Gera os tokens JWT automaticamente
        refresh = RefreshToken.for_user(user)

        return {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "access": str(refresh.access_token),  # Access Token
            "refresh": str(refresh),  # Refresh Token
        }


class UserLoginSerializer(serializers.Serializer):
    """Serializador para autenticação de usuários e geração de tokens"""
    
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        """Autenticação do usuário e retorno dos tokens JWT"""
        email = data.get("email")
        password = data.get("password")

        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError("Credenciais inválidas.")

        # Gera os tokens JWT
        refresh = RefreshToken.for_user(user)

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
            },
        }


class UserRecoverySerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        """Verifica se o e-mail está cadastrado e envia um OTP usando EmailService."""
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("E-mail não encontrado.")

        otp_code = OtpCode.objects.create(user=user, code=OtpCode.generate_otp())

        email_service = EmailService(
            subject="Código de Recuperação de Senha",
            to_email=[value],
            template_name="emails/recovery_email.html",
            context={"otp_code": otp_code.code, "user": user}
        )
        email_service.send()
        
        return value


class OtpVerifySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)

    def validate(self, data):
        """Valida o código OTP e gera um link temporário para redefinição de senha"""
        try:
            otp = OtpCode.objects.filter(code=data['code'], is_used=False).latest('created_at')
        except OtpCode.DoesNotExist:
            raise serializers.ValidationError({"code": "Código inválido ou expirado."})

        if not otp.is_valid():
            raise serializers.ValidationError({"code": "Código expirado."})

        # Marcar código como usado
        otp.mark_as_used()

        # Criar um token único para redefinição de senha
        reset_token = ResetPasswordToken.objects.create(user=otp.user)

        # Construir a URL de reset dinamicamente sempre com base em settings.SITE_URL
        domain = settings.SITE_URL if hasattr(settings, 'SITE_URL') else "http://127.0.0.1"
        reset_url = f"{domain}/auth/reset-password/?token={reset_token.token}"

        return {"reset_url": reset_url}


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        """Valida o token de redefinição e a nova senha"""
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "As senhas não coincidem."})

        try:
            reset_token = ResetPasswordToken.objects.get(token=data['token'])
        except ResetPasswordToken.DoesNotExist:
            raise serializers.ValidationError("Token inválido ou expirado.")

        if not reset_token.is_valid():
            raise serializers.ValidationError("Token expirado.")

        return data

    def save(self):
        """Atualiza a senha do usuário e exclui o token de reset"""
        reset_token = ResetPasswordToken.objects.get(token=self.validated_data['token'])
        user = reset_token.user
        user.set_password(self.validated_data['password'])
        user.save()

        # Excluir o token de reset após o uso
        reset_token.delete()

        # Enviar notificação com template HTML
        email_service = EmailService(
            subject="Sua senha foi alterada",
            to_email=[user.email],
            template_name="emails/password_changed.html",
            context={"user": user}
        )
        email_service.send()

        return {"message": "Senha redefinida com sucesso!"}
