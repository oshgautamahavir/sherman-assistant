from django.urls import path
from . import views

app_name = 'sherman'

urlpatterns = [
    path('scrape/', views.scrape_api, name='scrape_api'),
    path('chat/', views.chat_api, name='chat_api'),
    path('history/', views.history_api, name='history_api')
]

