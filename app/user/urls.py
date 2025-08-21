
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),

    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),

    # company crud
    path("add-company/", views.AddCompanyView.as_view(), name="add_company"),
    path("company/<int:pk>/edit/", views.EditCompanyView.as_view(), name="edit_company"),
    path("company/<int:pk>/delete/", views.DeleteCompanyView.as_view(), name="delete_company"),

    # hr crud
    path("add-hr/", views.AddHRView.as_view(), name="add_hr"),
    path("hr/<int:pk>/edit/", views.EditHRView.as_view(), name="edit_hr"),
    path("hr/<int:pk>/delete/", views.DeleteHRView.as_view(), name="delete_hr"),



   



    path("logout/", views.LogoutView.as_view(), name="logout"),


    # path('logout/', views.UserLogoutView.as_view(), name='logout'),
]