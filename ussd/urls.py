# from django.conf.urls import url

from django.urls import path, re_path
from . import views

urlpatterns = [
    re_path(r"^$", views.ussd_handler, name="ussd"),
    path("req/", views.debug_request_view, name="request"),
]
