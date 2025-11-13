from django.urls import path
from . import views

app_name = 'sherman'

urlpatterns = [
    path('scrape/', views.scrape_api, name='scrape_api'),
    # Add your API endpoints here
]

