from rest_framework.routers import DefaultRouter
from jobs.views import JobViewSet
from django.urls import path, include

router = DefaultRouter()
router.register(r'jobs', JobViewSet, basename='job')

urlpatterns = [
    path('', include(router.urls)),
]