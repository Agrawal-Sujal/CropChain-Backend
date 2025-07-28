from django.urls import path
from . import views

urlpatterns = [
    path("review/", views.show_pending_images, name="review-image"),
]
