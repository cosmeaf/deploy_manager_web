############################################
# FILE: deploy/urls.py
############################################
from django.urls import path
from . import views

# Removido app_name para evitar conflitos com templates existentes
urlpatterns = [
    path("", views.dashboard_home, name="dashboard_home"), 
    path("deploys/", views.dashboard, name="deploy_dashboard"), 
    path("run/<int:script_id>/", views.run_script, name="deploy_run"),
    path("stream/<int:script_id>/", views.stream_script, name="deploy_stream"),
    
    # Rotas do Editor de Secrets
    path("secrets/", views.list_secrets, name="list_secrets"),
    path("secrets/edit/<str:filename>/", views.edit_secret, name="edit_secret"),
    
    # Rota para depuração
    path("health/", views.health_check, name="health_check"),
]