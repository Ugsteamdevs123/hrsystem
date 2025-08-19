
from django.urls import path
from . import views

app_name = 'user'
urlpatterns = [
    path('hr/', views.HrDashboardView.as_view(), name='hr_dashboard'),
    path('department-team/', views.DepartmentTeamView.as_view(), name='department_team'),
    path('get-companies-and-department-teams/', views.GetCompaniesAndDepartmentTeamsView.as_view(), name='get_companies_and_department_teams'),
    # path('signup/', views.signup_view, name='signup'),
    # add any other user-related URLs
]