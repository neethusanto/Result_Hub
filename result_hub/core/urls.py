from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('faculty/', views.faculty_dashboard, name='faculty_dashboard'),
    path('upload/', views.upload, name='upload'),
    path('analytics/', views.analytics, name='analytics'),
    path('toppers/', views.toppers, name='toppers'),
    path('student/download/', views.download_marklist, name='download_marklist'),
    path('student/profile/edit/', views.edit_profile, name='edit_profile'),
]