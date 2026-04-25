"""
URL configuration for edu2job project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('login.html', TemplateView.as_view(template_name='login.html'), name='login'),
    path('register.html', TemplateView.as_view(template_name='register.html'), name='register'),
    path('dashboard.html', TemplateView.as_view(template_name='dashboard.html'), name='dashboard'),
    path('profile.html', TemplateView.as_view(template_name='profile.html'), name='profile'),
    path('predict.html', TemplateView.as_view(template_name='predict.html'), name='predict'),
    path('history.html', TemplateView.as_view(template_name='history.html'), name='history'),
    path('result.html', TemplateView.as_view(template_name='result.html'), name='result'),
    path('logout.html', TemplateView.as_view(template_name='logout.html'), name='logout'),
]

# Error handlers
handler400 = 'django.views.defaults.bad_request'
handler403 = 'django.views.defaults.permission_denied'
handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'
