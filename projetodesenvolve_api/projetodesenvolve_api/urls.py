from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="API Certificados Projeto Desenvolve",
        default_version="v1",
        description="API para download de CSV e PDF de certificados emitidos",
        contact=openapi.Contact(email="seuemail@exemplo.com"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # ADMIN
    path("admin/", admin.site.urls),

    # API
    path("api/certificados/", include("core.urls")),

    # ROOT = SWAGGER UI (ELIMINA 400 NO /)
    path("", schema_view.with_ui("swagger", cache_timeout=0), name="swagger-root"),

    # SWAGGER / REDOC EXPLÍCITOS
    re_path(r"^swagger(?P<format>\.json|\.yaml)$", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]
