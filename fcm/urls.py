from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.RegisterFCMToken.as_view(), name="review-image"),
    path("sendNotification/",view=views.sendNotification,name="send-notification")
]