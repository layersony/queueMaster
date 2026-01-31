from django.urls import path
from . import views

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('api/stats/', views.DashboardAPI.get_stats, name='dashboard_stats'),
    path('api/jobs/', views.DashboardAPI.get_jobs, name='dashboard_jobs'),
    path('api/jobs/<uuid:job_id>/', views.DashboardAPI.get_job_details, name='job_details'),
    path('api/dlq/', views.DashboardAPI.get_dlq_jobs, name='dlq_jobs'),
]