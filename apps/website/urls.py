from django.urls import path
from . import views

app_name = 'website'

urlpatterns = [
    path('', views.home, name='home'),
    path('about-us/', views.about, name='about'),
    path('contact-us/', views.contact, name='contact'),
    path('mutual-funds/', views.mutual_funds, name='mutual_funds'),
    path('privacypolicy/', views.privacypolicy, name='privacypolicy'),
    path('termscondition/', views.termscondition, name='termsandconditions'),
    path('documentsdownload/', views.documentsdownload, name='documentsdownload'),
    
]
