from django.urls import path
from . import views

urlpatterns = [
    path('', views.root, name='root'),
    path('face-rec/', views.face_rec, name='faceRec'),
     path('face-rec2/', views.face_rec2, name='faceRec2'),
    path('saml/face_rec_slo/', views.slo, name='face_rec_slo'),
    path('saml/face_rec_sls/', views.sls, name='face_rec_sls')
]