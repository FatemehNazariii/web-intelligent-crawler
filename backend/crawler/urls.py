from django.urls import path
from .views import crawl_topic

urlpatterns = [
    path("crawl/", crawl_topic),
]