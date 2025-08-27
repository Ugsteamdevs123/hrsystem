
from django.urls import path
from . import views

app_name = 'user'
urlpatterns = [
    path('hr/', views.HrDashboardView.as_view(), name='hr_dashboard'),
    path('department-team/', views.DepartmentTeamView.as_view(), name='department_team'),
    path('get-companies-and-department-teams/', views.GetCompaniesAndDepartmentTeamsView.as_view(), name='get_companies_and_department_teams'),
    
    path('company-summary/<int:company_id>/', views.CompanySummaryView.as_view(), name='company_summary'),
    path('department-table/<int:department_id>/', views.DepartmentTableView.as_view(), name='department_table'),
    path('create-data/<int:department_id>/', views.CreateDataView.as_view(), name='create_data'),
    path('get-data/<str:table>/<str:id>/', views.GetDataView.as_view(), name='get_data'),
    path('update-data/<int:department_id>/', views.UpdateDataView.as_view(), name='update_data'),
    path('delete-data/<str:table>/<int:id>/', views.DeleteDataView.as_view(), name='delete_data'),

    path('department-groups-sections/', views.DepartmentGroupsSectionsView.as_view(), name='department_groups_sections'),
    path('designations/', views.DesignationsView.as_view(), name='designations'),
    path('designations/create/', views.DesignationCreateView.as_view(), name='designation_create'),
    path('locations/', views.LocationsView.as_view(), name='locations'),
    path('employee-status-choices/', views.EmployeeStatusView.as_view(), name='employee_status_choices'),

    path('manage-formulas/', views.manage_formulas, name='manage_formulas'),
    path("get-model-fields/", views.get_model_fields, name="get_model_fields"),
    path('create-formula/', views.create_formula, name='create_formula'),
    path('edit-formula/<int:pk>/', views.edit_formula, name='edit_formula'),
    path('edit-field-formula/<int:pk>/', views.edit_field_formula, name='edit_field_formula'),

    path('get-company-departments-employees/', views.get_company_departments_employees, name='get_company_departments_employees'),
    path('get-department-employees/', views.get_department_employees, name='get_department_employees'),
]