
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),

    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),


    path("add-company/", views.AddCompanyView.as_view(), name="add_company"),

    path("add-hr/", views.AddHRView.as_view(), name="add_hr"),

    path("logout/", views.LogoutView.as_view(), name="logout"),


    # path('logout/', views.UserLogoutView.as_view(), name='logout'),
]