# from django.conf.urls import url

from django.urls import path, re_path
from . import views

urlpatterns = [
    re_path(r"^$", views.index, name="index"),
    # path('index/', views.index, name="index")
]
