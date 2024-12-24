from django.shortcuts import render
from django.urls import path
from . import views

urlpatterns = [
    path('', views.acs, name='acs'),
    path('saml/slo/', views.slo, name='slo'),
    path('saml/sls/', views.sls, name='sls'),
]

handler404 = 'core.views.error_404'
handler500 = 'core.views.error_500'