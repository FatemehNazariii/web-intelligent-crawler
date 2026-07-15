from django.urls import path
from . import views

urlpatterns = [
    path('api/chat/', views.chat_api, name='chat_api'),
    path('api/research/', views.research_api, name='research_api'),
    path('api/qa/', views.qa_api, name='qa_api'),
    path('api/translate/', views.translate_api, name='translate_api'),
]