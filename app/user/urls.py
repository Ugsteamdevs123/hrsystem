
from django.urls import path
from . import views

# app_name = 'user'
urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path("logout/", views.LogoutView.as_view(), name="logout"),

    # user crud
    path("add-user/", views.AddUserView.as_view(), name="add_user"),
    path("user/<int:pk>/edit/", views.UpdateUserView.as_view(), name="update_user"),
    path("users/", views.ViewUsersView.as_view(), name="view_users"),
    path("user/<int:pk>/delete/", views.DeleteUserView.as_view(), name="delete_user"),

    # For password reset
    path("reset-password/", views.CustomPasswordChangeView.as_view(), name="password_change"),    


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

    # formula crud
    path('formula/create/', views.CreateFormulaView.as_view(), name='create_formula'),
    path('formula/view/', views.FormulaListView.as_view(), name='view_formula'),
    path('formula/edit/<int:pk>/', views.EditFormulaView.as_view(), name='edit_formula'),

    # manage formula crud 
    path('field-formulas/', views.FieldFormulaListView.as_view(), name='view_field_formulas'),
    path('field-formulas/create/', views.CreateFieldFormulaView.as_view(), name='create_field_formula'),
    path('field-formulas/edit/<int:pk>/', views.EditFieldFormulaView.as_view(), name='edit_field_formula'),

    # manage vehicle CRUD
    path('vehicles/', views.ViewVehicleListView.as_view(), name='view_vehicles'),
    path('vehicles/add/', views.AddVehicleView.as_view(), name='add_vehicle'),
    path('vehicles/update/<int:pk>/', views.UpdateVehicleView.as_view(), name='update_vehicle'),
    path('vehicles/delete/<int:pk>/', views.DeleteVehicleView.as_view(), name='delete_vehicle'),
    path('vehicles_brands/add/', views.AddVehicleBrandView.as_view(), name='add_vehicle_brand'),
    path('vehicles_brands/edit/<int:pk>/', views.AddVehicleBrandView.as_view(), name='edit_vehicle_brand'),
    path('vehicles_brands/delete/<int:pk>/', views.DeleteVehicleBrandView.as_view(), name='delete_vehicle_brand'),

    #manage HR Dashboard CRUD
    path('hr/', views.HrDashboardView.as_view(), name='hr_dashboard'),
    path('hr/approved/', views.HrUpdateApprovedView.as_view(), name='hr_approved'),
    path('hr/final-approve/', views.HrFinalApproveSummaryView.as_view(), name='hr_final_approve'),
    path('department-team/', views.DepartmentTeamView.as_view(), name='department_team'),
    path('department-teams/', views.CompanyDepartmentTeamView.as_view(), name='company_department_team'),
    path('get-companies-and-department-teams/', views.GetCompaniesAndDepartmentTeamsView.as_view(), name='get_companies_and_department_teams'),
    path('company-summary/<int:company_id>/', views.CompanySummaryView.as_view(), name='company_summary'),

    # For employee crud
    path('employee/', views.EmployeesView.as_view(), name='employees_view'),
    path('employee/create/', views.CreateEmployeeView.as_view(), name='create_employee'),
    path('employee/update/<int:employee_id>/', views.UpdateEmployeeView.as_view(), name='update_employee'),
    path('department/delete/<int:employee_id>/', views.DeleteEmployeeView.as_view(), name='delete_employee'),
    path('employee/<int:employee_id>/', views.EmployeeDetailView.as_view(), name='employee_detail'),

    # For dept table crud
    path('department/<int:department_id>/', views.DepartmentTableView.as_view(), name='department_table'),
    # path('department/<int:department_id>/create/', views.CreateEmployeeView.as_view(), name='create_employee'),
    # path('department/<int:department_id>/update/<int:employee_id>/', views.UpdateEmployeeView.as_view(), name='update_employee'),
    # path('department/<int:department_id>/delete/<int:employee_id>/', views.DeleteEmployeeView.as_view(), name='delete_employee'),
    path('get-data/<str:table>/<str:id>/', views.GetDataView.as_view(), name='get_data'),
    path('save-draft/<int:department_id>/', views.SaveDraftView.as_view(), name='save_draft'),
    path('save-final/<int:department_id>/', views.SaveFinalView.as_view(), name='save_final'),
    path('get-formulas/', views.GetFormulasView.as_view(), name='get_formula'),


    path('department-groups-sections/', views.DepartmentGroupsSectionsView.as_view(), name='department_groups_sections'),
    path('designations/', views.DesignationsView.as_view(), name='designations'),
    path('designations/create/', views.DesignationCreateView.as_view(), name='designation_create'),
    path('locations/', views.LocationsView.as_view(), name='locations'),
    path('employee-status-choices/', views.EmployeeStatusView.as_view(), name='employee_status_choices'),

    path("get-model-fields/", views.GetModelFieldsView.as_view(), name="get_model_fields"),

    path('get-company-departments-employees/', views.GetCompanyDepartmentsEmployeesView.as_view(), name='get_company_departments_employees'),
    path('get-department-employees/', views.GetDepartmentEmployeesView.as_view(), name='get_department_employees'),

    path('vehicles-dropdown/', views.VehiclesDropdownView.as_view(), name='vehicles-dropdown'),

    path('configurations/', views.ManageConfigurationsView.as_view(), name='manage_configurations'),

    path('create-dynamic-attribute/', views.CreateDynamicAttributeView.as_view(), name='create_dynamic_attribute')
]