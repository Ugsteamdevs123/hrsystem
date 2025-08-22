
from django.urls import path
from . import views

# app_name = 'user'
urlpatterns = [
    path('hr/', views.HrDashboardView.as_view(), name='hr_dashboard'),
    path('department-team/', views.DepartmentTeamView.as_view(), name='department_team'),
    path('get-companies-and-department-teams/', views.GetCompaniesAndDepartmentTeamsView.as_view(), name='get_companies_and_department_teams'),
    
    path('company-summary/<int:company_id>/', views.CompanySummaryView.as_view(), name='company_summary'),
    path('department-table/<int:department_id>/', views.DepartmentTableView.as_view(), name='department_table'),
    path('create-data/<int:department_id>/', views.CreateDataView.as_view(), name='create_data'),
    path('delete-data/<str:table>/<int:id>/', views.DeleteDataView.as_view(), name='delete_data'),

    path('department-groups-sections/', views.DepartmentGroupsSectionsView.as_view(), name='department_groups_sections'),
    path('designations/', views.DesignationsView.as_view(), name='designations'),
    path('designations/create/', views.DesignationCreateView.as_view(), name='designation_create'),
    path('locations/', views.LocationsView.as_view(), name='locations'),
    
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