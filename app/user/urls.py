
from django.urls import path
from . import views

# app_name = 'user'
urlpatterns = [

    path('login/', views.LoginView.as_view(), name='login'),

    # user crud
    path("add-user/", views.AddUserView.as_view(), name="add_user"),
    path("user/<int:pk>/edit/", views.UpdateUserView.as_view(), name="update_user"),
    path("users/", views.ViewUsersView.as_view(), name="view_users"),
    path("user/<int:pk>/delete/", views.DeleteUserView.as_view(), name="delete_user"),


    # company crud
    path('company/' , views.ViewCompaniesView.as_view() , name='view_company'),
    path("add-company/", views.AddCompanyView.as_view(), name="add_company"),
    path("company/<int:pk>/edit/", views.UpdateCompanyView.as_view(), name="update_company"),
    path("company/<int:pk>/delete/", views.DeleteCompanyView.as_view(), name="delete_company"),
    
    # Section CRUD
    path('section/', views.ViewSectionsView.as_view(), name='view_section'),
    path('add-section/', views.AddSectionView.as_view(), name='add_section'),
    path('section/<int:pk>/edit/', views.UpdateSectionView.as_view(), name='update_section'),
    path('section/<int:pk>/delete/', views.DeleteSectionView.as_view(), name='delete_section'),

    # dept groups CRUD
    path('department-groups/', views.ViewDepartmentGroupsView.as_view(), name='view_departmentgroups'),
    path('add-department-group/', views.AddDepartmentGroupView.as_view(), name='add_departmentgroups'),
    path('department-groups/<int:pk>/edit/', views.UpdateDepartmentGroupView.as_view(), name='update_departmentgroups'),
    path('department-groups/<int:pk>/delete/', views.DeleteDepartmentGroupView.as_view(), name='delete_departmentgroups'),

    # hr assign company crud
    path('hr-assigned-companies/', views.ViewHrAssignedCompaniesView.as_view(), name='view_hr_assigned_companies'),
    path('add-hr-assigned-company/', views.AddHrAssignedCompanyView.as_view(), name='add_hr_assigned_company'),
    path('hr-assigned-companies/<int:pk>/edit/', views.UpdateHrAssignedCompanyView.as_view(), name='update_hr_assigned_company'),
    path('hr-assigned-companies/<int:pk>/delete/', views.DeleteHrAssignedCompanyView.as_view(), name='delete_hr_assigned_company'),

    # vehicle crud
    path("vehicles/", views.ViewVehicleListView.as_view(), name="view_vehicles"),
    path("vehicles/add/", views.AddVehicleView.as_view(), name="add_vehicle"),
    path("vehicles/update/<int:pk>/", views.UpdateVehicleView.as_view(), name="update_vehicle"),
    path("vehicles/delete/<int:pk>/", views.DeleteVehicleView.as_view(), name="delete_vehicle"),



    path('hr/', views.HrDashboardView.as_view(), name='hr_dashboard'),
    path('department-team/', views.DepartmentTeamView.as_view(), name='department_team'),
    path('get-companies-and-department-teams/', views.GetCompaniesAndDepartmentTeamsView.as_view(), name='get_companies_and_department_teams'),
    
    path('company-summary/<int:company_id>/', views.CompanySummaryView.as_view(), name='company_summary'),

    path('department-table/<int:department_id>/', views.DepartmentTableView.as_view(), name='department_table'),
    path('get-data/employee/<int:employee_id>/', views.GetEmployeeDataView.as_view(), name='get_employee_data'),
    
    
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
    path('vehicles-dropdown/', views.VehiclesDropdownView.as_view(), name='vehicles-dropdown'),


    # path("dashboard/", views.DashboardView.as_view(), name="dashboard"),

    

    



   



    path("logout/", views.LogoutView.as_view(), name="logout"),


    # path('logout/', views.UserLogoutView.as_view(), name='logout'),
]