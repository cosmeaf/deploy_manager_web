from django.contrib.auth import get_user_model
from rest_framework import viewsets, status
from rest_framework.response import Response
from .serializers import UserRegisterSerializer, UserLoginSerializer, UserRecoverySerializer, OtpVerifySerializer, ResetPasswordSerializer
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

User = get_user_model()

class UserBlockViewSet(viewsets.ViewSet):
    """
    Endpoint para bloquear/desativar usuários
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Bloqueia um usuário pelo username",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["username"],
            properties={
                "username": openapi.Schema(type=openapi.TYPE_STRING, description="Nome do usuário a ser bloqueado"),
            },
        ),
        responses={200: "Usuário bloqueado com sucesso", 404: "Usuário não encontrado"},
    )
    def create(self, request):
        username = request.data.get("username")

        if not username:
            return Response({"error": "O campo 'username' é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(username=username)
            user.is_active = False
            user.save()
            return Response({"message": f"Usuário {username} bloqueado com sucesso."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "Usuário não encontrado."}, status=status.HTTP_404_NOT_FOUND)


class UserBlockViewSet(viewsets.ViewSet):
    """
    Endpoint para bloquear/desativar usuários
    """
    permission_classes = [IsAuthenticated]

    def create(self, request):
        username = request.data.get("username")

        if not username:
            return Response({"error": "O campo 'username' é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(username=username)
            user.is_active = False
            user.save()
            return Response({"message": f"Usuário {username} bloqueado com sucesso."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "Usuário não encontrado."}, status=status.HTTP_404_NOT_FOUND)


class UserRegisterViewSet(viewsets.ModelViewSet):
    """ViewSet para registro de usuários"""
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    http_method_names = ['post']

    def create(self, request, *args, **kwargs):
        """Método para registrar um novo usuário"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.save(), status=status.HTTP_201_CREATED) 
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginViewSet(viewsets.ModelViewSet):
    """ViewSet para login de usuários"""
    queryset = User.objects.none()
    serializer_class = UserLoginSerializer
    http_method_names = ['post']

    def create(self, request, *args, **kwargs):
        """Método para autenticação de usuários"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserRecoveryViewSet(viewsets.ModelViewSet):
    """Recebe um e-mail e envia código OTP"""
    serializer_class = UserRecoverySerializer
    queryset = []
    
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            return Response({"message": "Código OTP enviado para o e-mail."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OtpVerifyViewSet(viewsets.ModelViewSet):
    """Verifica o OTP e retorna URL para reset"""
    serializer_class = OtpVerifySerializer
    queryset = []
    
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResetPasswordViewSet(viewsets.ModelViewSet):
    """Permite redefinir senha"""
    serializer_class = ResetPasswordSerializer
    queryset = []
    
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Senha redefinida com sucesso."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)