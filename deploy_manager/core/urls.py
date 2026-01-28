from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Autenticação
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('accounts/password-change/', auth_views.PasswordChangeView.as_view(template_name='registration/password_change_form.html', success_url='/'), name='password_change'),
    
    # App Principal
    path('', include('deploy.urls')),
]