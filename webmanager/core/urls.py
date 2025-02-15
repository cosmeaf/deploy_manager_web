from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from rest_framework.response import Response
from rest_framework.decorators import api_view
from authentication.views import UserRegisterViewSet, UserLoginViewSet, UserBlockViewSet, UserRecoveryViewSet, OtpVerifyViewSet, ResetPasswordViewSet

from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Criar o Schema do Swagger
schema_view = get_schema_view(
    openapi.Info(
        title="WebManager API",
        default_version="v1",
        description="Documentação da API do WebManager",
        terms_of_service="https://lexlam.com.br/terms/",
        contact=openapi.Contact(email="support@lexlam.com.br"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
)

# Criar um router e registrar as views padrão
router = SimpleRouter()
router.register(r'auth/register', UserRegisterViewSet, basename='user-register')
router.register(r'auth/login', UserLoginViewSet, basename='user-login')
router.register(r'auth/block', UserBlockViewSet, basename='user-block')
router.register(r'auth/recovery', UserRecoveryViewSet, basename='user-recovery')
router.register(r'auth/otp-verify', OtpVerifyViewSet, basename='otp-verify')
router.register(r'auth/reset-password', ResetPasswordViewSet, basename='reset-password')

# Criar API Root personalizada sem /api/
@api_view(['GET'])
def api_root(request, format=None):
    return Response({
        "auth/register": request.build_absolute_uri('auth/register/'),
        "auth/login": request.build_absolute_uri('auth/login/'),
        "auth/block": request.build_absolute_uri('auth/block/'),
        "auth/recovery": request.build_absolute_uri('auth/recovery/'),
        "auth/otp-verify": request.build_absolute_uri('auth/otp-verify/'),
        "auth/reset-password": request.build_absolute_uri('auth/reset-password/'),
        "auth/refresh": request.build_absolute_uri('auth/refresh/'),
        "auth/verify": request.build_absolute_uri('auth/verify/'),
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', api_root, name='api-root'),
    path('', include(router.urls)),

    # Endpoints JWT Refresh e Verify
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Documentação Swagger e Redoc
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]
