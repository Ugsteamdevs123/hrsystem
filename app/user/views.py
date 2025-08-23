from rest_framework.views import APIView
from rest_framework.response import Response


from .serializers import (
    UserLoginSerializer,
)
from .models import (
    CustomUser,
    Company
)

from django.contrib.auth import login, logout
from rest_framework import status
from django.middleware.csrf import get_token
from rest_framework.permissions import AllowAny , IsAuthenticated
from rest_framework.authentication import SessionAuthentication

from django.contrib.auth.mixins import PermissionRequiredMixin



from django.views import View
from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import (
    CompanyForm , 
    CustomUserForm,
    CustomUserUpdateForm,

)

# Create your views here.

class LoginView(View):
    template_name = "login.html"

    def get(self, request):
        """Handles GET requests and renders the login form."""
        return render(request, self.template_name)

    def post(self, request):
        """Handles POST requests and authenticates users."""
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(username=email, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                if user.is_superuser:
                    # Redirect superuser to view users page
                    return redirect("view_users")
                else:
                    # Placeholder for normal users (empty page for now)
                    return render(request, "normal_user_home.html")
            else:
                messages.error(request, "Your account is disabled.")
        else:
            messages.error(request, "Invalid email or password.")

        return render(request, self.template_name)



# --- CREATE USER ---
class AddUserView(PermissionRequiredMixin, View):
    permission_required = "user.add_customuser"
    template_name = "add_user.html"

    def get(self, request):
        form = CustomUserForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = CustomUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.is_staff = True
            user.is_superuser = False
            user.save()
            messages.success(request, "User added successfully!")
            return redirect("view_users")
        return render(request, self.template_name, {"form": form})



# --- UPDATE USER ---
class UpdateUserView(PermissionRequiredMixin, View):
    permission_required = "user.change_customuser"
    template_name = "update_user.html"

    def get(self, request, pk):
        user = get_object_or_404(
            CustomUser,
            pk=pk,
            is_deleted=False,
            is_staff=True,
            is_superuser=False,
        )
        form = CustomUserUpdateForm(instance=user)
        return render(request, self.template_name, {"form": form, "user": user})

    def post(self, request, pk):
        user = get_object_or_404(
            CustomUser,
            pk=pk,
            is_deleted=False,
            is_staff=True,
            is_superuser=False,
        )
        form = CustomUserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save()
            user.is_staff = True
            user.is_superuser = False
            user.save()
            messages.success(request, "User updated successfully!")
            return redirect("view_users")
        return render(request, self.template_name, {"form": form, "user": user})



# --- DELETE USER (soft delete) ---
class DeleteUserView(PermissionRequiredMixin, View):
    permission_required = "user.delete_customuser"

    def get(self, request, pk):
        user = get_object_or_404(
            CustomUser,
            pk=pk,
            is_staff=True,
            is_superuser=False,
        )
        user.is_deleted = True
        user.save()
        messages.success(request, "User deleted successfully")
        return redirect("view_users")




# --- VIEW USERS ---
class ViewUsersView(PermissionRequiredMixin, View):
    permission_required = "user.view_customuser"
    template_name = "view_users.html"

    def get(self, request):
        users = CustomUser.objects.filter(
            is_staff=True,
            is_deleted=False,
            is_superuser=False
        ).select_related("gender").prefetch_related("groups")  # ✅ fetch groups too

        # attach a selected_group attribute to each user
        for user in users:
            user.selected_group = user.groups.first()  # None if no group

        return render(request, self.template_name, {"users": users})


# --- VIEW COMPANIES ---
class ViewCompaniesView(PermissionRequiredMixin, View):
    permission_required = "app.view_company"  # replace 'app' with your app name
    template_name = "view_company.html"

    def get(self, request):
        companies = Company.objects.filter(is_deleted=False)
        return render(request, self.template_name, {"companies": companies})


# --- ADD COMPANY ---
class AddCompanyView(PermissionRequiredMixin, View):
    permission_required = "app.add_company"  # 🔑 change 'app' to your app name
    template_name = "add_company.html"

    def get(self, request):
        form = CompanyForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = CompanyForm(request.POST)
        if form.is_valid():
            company = form.save(commit=False)
            company.is_deleted = False
            company.save()
            messages.success(request, "Company added successfully!")
            return redirect("view_company")  # 🔄 go to companies list
        return render(request, self.template_name, {"form": form})



# --- UPDATE COMPANY ---
class UpdateCompanyView(PermissionRequiredMixin, View):
    permission_required = "app.change_company"
    template_name = "update_company.html"

    def get(self, request, pk):
        company = get_object_or_404(Company, pk=pk, is_deleted=False)
        form = CompanyForm(instance=company)
        return render(request, self.template_name, {"form": form, "company": company})

    def post(self, request, pk):
        company = get_object_or_404(Company, pk=pk, is_deleted=False)
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, "Company updated successfully!")
            return redirect("view_company")
        return render(request, self.template_name, {"form": form, "company": company})



# --- DELETE COMPANY ---
class DeleteCompanyView(PermissionRequiredMixin, View):
    permission_required = "app.delete_company"

    def get(self, request, pk):
        company = get_object_or_404(Company, pk=pk, is_deleted=False)
        company.is_deleted = True  # ✅ soft delete only active companies
        company.save()
        messages.success(request, "Company deleted successfully!")
        return redirect("view_company")



class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect("login")  # Replace with your login URL name





















from venv import logger
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.messages import success as messages_success
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import View
from django.contrib.sessions.models import Session

from permissions import GroupOrSuperuserPermission, PermissionRequiredMixin

from .models import (
    hr_assigned_companies,
    DepartmentTeams,
    IncrementDetailsSummary,
    Company,
    Employee,
    CurrentPackageDetails,
    ProposedPackageDetails,
    FinancialImpactPerMonth,
    DepartmentGroups,
    Designation,
    Location)

from .utils import get_companies_and_department_teams
from .serializer import (
    IncrementDetailsSummarySerializer,
    DepartmentGroupsSerializer,
    DesignationSerializer,
    DesignationCreateSerializer,
    LocationsSerializer

)
from collections import defaultdict
import json






class HrDashboardView(PermissionRequiredMixin, View):
    """
    Class-based view for HR dashboard.
    Handles PATCH requests to update 'eligible_for_increment' value.
    Renders HR dashboard page for GET requests.
    """
    permission_classes = [GroupOrSuperuserPermission]
    group_name = 'Hr'  # Set the group name for the permission

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view
    
    def get(self, request):
        # Fetch companies assigned to the logged-in HR

        company_data = get_companies_and_department_teams(request.user)

        # Handle AJAX request for employee data
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            
            company_id = request.GET.get('company_id')
            if not company_id:
                return JsonResponse({'error': 'No company ID provided'}, status=400)
            try:
                increment_details_summary = IncrementDetailsSummary.objects.filter(company__id=company_id)
                print(increment_details_summary)
                if increment_details_summary.exists():
                    data = IncrementDetailsSummarySerializer(increment_details_summary, many=True).data
                else:
                    # create a dict with all serializer fields set to None
                    # fields = IncrementDetailsSummarySerializer().get_fields().keys()
                    data = []

                return JsonResponse({'data': data})
            except DepartmentTeams.DoesNotExist:
                return JsonResponse({'data': []})

        # logger.info(f"User {request.user.username} accessed HR dashboard with {len(company_data)} companies")
        return render(request, 'hr_dashboard.html', {'company_data': company_data})

    def patch(self, request):
        # Handle AJAX PATCH request to update eligible_for_increment
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                data = json.loads(request.body)
                print(data)
                summary_id = data.get('id')
                eligible_for_increment = data.get('eligible_for_increment')
                if not summary_id or not eligible_for_increment:
                    return JsonResponse({'error': 'Invalid data'}, status=400)
                summary = IncrementDetailsSummary.objects.get(id=summary_id, company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company'))
                summary.eligible_for_increment = int(eligible_for_increment)
                summary.save()
                return JsonResponse({'message': 'Updated successfully'})
            except (IncrementDetailsSummary.DoesNotExist, ValueError):
                return JsonResponse({'error': 'Invalid ID or value'}, status=400)
        return JsonResponse({'error': 'Invalid request'}, status=400)


class DepartmentTeamView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def get(self, request):

        company_data = get_companies_and_department_teams(request.user)

        return render(request, 'department_team.html', {'company_data': company_data})

    def post(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                company_id = request.POST.get('company_id')
                name = request.POST.get('name')
                if not company_id or not name:
                    return JsonResponse({'error': 'Company and name are required'}, status=400)
                company = Company.objects.get(id=company_id, id__in=hr_assigned_companies.objects.filter(hr=request.user).values('company'))
                DepartmentTeams.objects.create(company=company, name=name)
                return JsonResponse({'message': 'Department added successfully'})
            except (Company.DoesNotExist, ValueError):
                return JsonResponse({'error': 'Invalid company or data'}, status=400)
        return JsonResponse({'error': 'Invalid request'}, status=400)

    def patch(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                data = json.loads(request.body)
                department_id = data.get('id')
                name = data.get('name').strip()
                if not department_id or not name:
                    return JsonResponse({'error': 'Department ID and name are required'}, status=400)
                department = DepartmentTeams.objects.get(
                    id=department_id,
                    company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
                )
                department.name = name
                department.save()
                return JsonResponse({'message': 'Department updated successfully'})
            except (DepartmentTeams.DoesNotExist, ValueError):
                return JsonResponse({'error': 'Invalid department or data'}, status=400)
        return JsonResponse({'error': 'Invalid request'}, status=400)

    def delete(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                data = json.loads(request.body)
                department_id = data.get('id')
                if not department_id:
                    return JsonResponse({'error': 'Department ID is required'}, status=400)
                department = DepartmentTeams.objects.get(
                    id=department_id,
                    company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
                )
                department.delete()  # Cascades to IncrementDetailsSummary due to on_delete=models.CASCADE
                return JsonResponse({'message': 'Department deleted successfully'})
            except (DepartmentTeams.DoesNotExist, ValueError):
                return JsonResponse({'error': 'Invalid department'}, status=400)
        return JsonResponse({'error': 'Invalid request'}, status=400)


class GetCompaniesAndDepartmentTeamsView(PermissionRequiredMixin, View):
    """
    Class-based view for fetching companies and departments teams list assigned to HR.
    """
    permission_classes = [GroupOrSuperuserPermission]
    group_name = 'Hr'  # Set the group name for the permission

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        return view
    
    def get(self, request):
        try:
            data = get_companies_and_department_teams(request.user)

            return JsonResponse({'data': data})  # Return companies for add_department.html
        except Exception as e:
            print(e)









class CompanySummaryView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def get(self, request, company_id):
        if not hr_assigned_companies.objects.filter(hr=request.user, company_id=company_id).exists():
            return render(request, 'error.html', {'error': 'Invalid company'}, status=400)

        company_data = get_companies_and_department_teams(request.user)

        company = Company.objects.get(id=company_id)
        increment_details_summary = IncrementDetailsSummary.objects.filter(company_id=company_id)
        if increment_details_summary.exists():
            data = IncrementDetailsSummarySerializer(increment_details_summary, many=True).data
            table_html = '<table class="table table-bordered custom-table">'
            table_html += '<thead><tr>'
            # Use serializer field names (with spaces) for headers, exclude 'id'
            headers = [key for key in data[0].keys() if key != 'id']
            for header in headers:
                table_html += f'<th class="font-weight-bold border-end">{header.title()}</th>'
            table_html += '<th class="font-weight-bold border-end">Actions</th></tr></thead><tbody>'
            for row in data:
                table_html += f'<tr data-id="{row["id"]}" data-eligible="{row["eligible for increment"] if row["eligible for increment"] is not None else ""}">'
                for header in headers:
                    table_html += f'<td class="border-end">{row[header] if row[header] is not None else ""}</td>'
                table_html += '<td class="border-end"><button class="btn btn-sm btn-primary edit-btn">Edit</button></td>'
                table_html += '</tr>'
            table_html += '</tbody></table>'
        else:
            table_html = '<p>No summary data available for this company.</p>'
        # logger.info(f"User {request.user.username} accessed summary for company {company_id}")
        return render(request, 'company_summary.html', {'company_data': company_data, 'company': company, 'table_html': table_html})

    def patch(self, request, company_id):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                # logger.debug(f"PATCH received: {request.POST}")
                data = json.loads(request.body)
                summary_id = data.get('id')
                eligible_for_increment = data.get('eligible_for_increment')
                if not summary_id or not eligible_for_increment:
                    return JsonResponse({'error': 'Invalid data'}, status=400)
                summary = IncrementDetailsSummary.objects.get(
                    id=summary_id,
                    company_id=company_id,
                    company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
                )
                summary.eligible_for_increment = int(eligible_for_increment)
                summary.save()
                # logger.debug(f"Updated summary {summary_id}: eligible_for_increment={eligible_for_increment}")
                return JsonResponse({'message': 'Updated successfully'})
            except (IncrementDetailsSummary.DoesNotExist, ValueError):
                # logger.error(f"Error updating summary: {request.POST}")
                return JsonResponse({'error': 'Invalid ID or value'}, status=400)
        return JsonResponse({'error': 'Invalid request'}, status=400)


class DepartmentTableView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def get(self, request, department_id):
        department = DepartmentTeams.objects.filter(
            id=department_id,
            company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
        ).first()
        if not department:
            return render(request, 'error.html', {'error': 'Invalid department'}, status=400)

        company_data = get_companies_and_department_teams(request.user)

        employees = Employee.objects.filter(department_team=department)
        joined_data = []
        for employee in employees:
            current_package = CurrentPackageDetails.objects.filter(employee=employee).first() or {}
            proposed_package = ProposedPackageDetails.objects.filter(employee=employee).first() or {}
            financial_impact = FinancialImpactPerMonth.objects.filter(employee=employee).first() or {}
            joined_data.append({
                'employee_id': employee.emp_id,
                'fullname': employee.fullname,
                'company': employee.company.name,
                'department_team': employee.department_team.name if employee.department_team else '',
                'department_group': employee.department_group.name if employee.department_group else '',
                'section': employee.section.name if employee.section else '',
                'designation': employee.designation.title if employee.designation else '',
                'location': employee.location.location if employee.location else '',
                'date_of_joining': employee.date_of_joining or '',
                'resign': employee.resign,
                'date_of_resignation': employee.date_of_resignation or '',
                'remarks': employee.remarks or '',
                'image': employee.image.url if employee.image else '',
                'gross_salary': current_package.gross_salary if current_package else '',
                'vehicle': current_package.vehicle if current_package else '',
                'fuel_limit': current_package.fuel_limit if current_package else '',
                'mobile_allowance_current': current_package.mobile_allowance if current_package else '',
                'increment_percentage': proposed_package.increment_percentage if proposed_package else '',
                'increased_amount': proposed_package.increased_amount.formula if proposed_package and proposed_package.increased_amount else '',
                'revised_salary': proposed_package.revised_salary.formula if proposed_package and proposed_package.revised_salary else '',
                'increased_fuel_amount': proposed_package.increased_fuel_amount if proposed_package else '',
                'revised_fuel_allowance': proposed_package.revised_fuel_allowance.formula if proposed_package and proposed_package.revised_fuel_allowance else '',
                'mobile_allowance_proposed': proposed_package.mobile_allowance if proposed_package else '',
                'vehicle_proposed': proposed_package.vehicle if proposed_package else '',
                'emp_status': financial_impact.emp_status.name if financial_impact and financial_impact.emp_status else '',
                'serving_years': financial_impact.serving_years if financial_impact else '',
                'salary': financial_impact.salary if financial_impact else '',
                'gratuity': financial_impact.gratuity.formula if financial_impact and financial_impact.gratuity else '',
                'bonus': financial_impact.bonus.formula if financial_impact and financial_impact.bonus else '',
                'leave_encashment': financial_impact.leave_encashment.formula if financial_impact and financial_impact.leave_encashment else '',
                'mobile_allowance_financial': financial_impact.mobile_allowance.formula if financial_impact and financial_impact.mobile_allowance else '',
                'fuel': financial_impact.fuel if financial_impact else '',
                'total': financial_impact.total.formula if financial_impact and financial_impact.total else '',
            })

        if joined_data:
            table_html = '<div class="table-responsive"><table class="table table-striped table-hover">'
            table_html += '<thead><tr>'
            for key in joined_data[0].keys():
                table_html += f'<th>{key.replace("_", " ").title()}</th>'
            table_html += '<th>Actions</th></tr></thead><tbody>'
            for row in joined_data:
                table_html += f'<tr data-employee-id="{row["employee_id"]}">'
                for value in row.values():
                    table_html += f'<td>{value if value is not None else ""}</td>'
                table_html += '<td><button class="btn btn-sm btn-danger delete-employee-btn">Delete</button></td>'
                table_html += '</tr>'
            table_html += '</tbody></table></div>'
        else:
            table_html = '<p>No data available for this department.</p>'

        return render(request, 'department_table.html', {
            'department': department,
            'table_html': table_html,
            'department_id': department_id,
            'company_data': company_data
        })


class CreateDataView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def get(self, request, department_id):
        department = DepartmentTeams.objects.filter(
            id=department_id,
            company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
        ).first()
        if not department:
            return render(request, 'error.html', {'error': 'Invalid department'}, status=400)
        return render(request, 'create_data.html', {
            'department_id': department_id,
            'company_id': department.company.id
        })

    def post(self, request, department_id):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                print(request.POST)
                step = request.POST.get('step')
                department = DepartmentTeams.objects.get(
                    id=department_id,
                    company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
                )
                if step == 'employee':
                    employee = Employee.objects.create(
                        fullname=request.POST.get('fullname'),
                        company=department.company,
                        department_team=department,
                        department_group_id=request.POST.get('department_group_id'),
                        section_id=request.POST.get('section_id'),
                        designation_id=request.POST.get('designation_id'),
                        location_id=request.POST.get('location_id'),
                        date_of_joining=request.POST.get('date_of_joining'),
                        resign=request.POST.get('resign') == 'true',
                        date_of_resignation=request.POST.get('date_of_resignation') or None,
                        remarks=request.POST.get('remarks') or '',
                        image=request.FILES.get('image') if 'image' in request.FILES else None
                    )
                    logger.debug(f"Employee created: {employee.emp_id}")
                    return JsonResponse({'message': 'Employee created', 'employee_id': employee.emp_id})
                elif step == 'current_package':
                    employee_id = request.POST.get('employee_id')
                    employee = Employee.objects.get(emp_id=employee_id, department_team=department)
                    current_package = CurrentPackageDetails.objects.create(
                        employee=employee,
                        gross_salary=request.POST.get('gross_salary'),
                        vehicle=request.POST.get('vehicle'),
                        fuel_limit=request.POST.get('fuel_limit'),
                        mobile_allowance=request.POST.get('mobile_allowance')
                    )
                    logger.debug(f"CurrentPackageDetails created for employee: {employee_id}")
                    return JsonResponse({'message': 'Current Package created'})
                elif step == 'proposed_package':
                    employee_id = request.POST.get('employee_id')
                    employee = Employee.objects.get(emp_id=employee_id, department_team=department)
                    proposed_package = ProposedPackageDetails.objects.create(
                        employee=employee,
                        increment_percentage=request.POST.get('increment_percentage'),
                        increased_amount_id=request.POST.get('increased_amount_id'),
                        revised_salary_id=request.POST.get('revised_salary_id'),
                        increased_fuel_amount=request.POST.get('increased_fuel_amount'),
                        revised_fuel_allowance_id=request.POST.get('revised_fuel_allowance_id'),
                        mobile_allowance=request.POST.get('mobile_allowance'),
                        vehicle=request.POST.get('vehicle')
                    )
                    logger.debug(f"ProposedPackageDetails created for employee: {employee_id}")
                    return JsonResponse({'message': 'Proposed Package created'})
                elif step == 'financial_impact':
                    employee_id = request.POST.get('employee_id')
                    employee = Employee.objects.get(emp_id=employee_id, department_team=department)
                    financial_impact = FinancialImpactPerMonth.objects.create(
                        employee=employee,
                        emp_status_id=request.POST.get('emp_status_id'),
                        serving_years=request.POST.get('serving_years'),
                        salary=request.POST.get('salary'),
                        gratuity_id=request.POST.get('gratuity_id'),
                        bonus_id=request.POST.get('bonus_id'),
                        leave_encashment_id=request.POST.get('leave_encashment_id'),
                        mobile_allowance_id=request.POST.get('mobile_allowance_id'),
                        fuel=request.POST.get('fuel'),
                        total_id=request.POST.get('total_id')
                    )
                    logger.debug(f"FinancialImpactPerMonth created for employee: {employee_id}")
                    return JsonResponse({'message': 'Financial Impact created'})
                return JsonResponse({'error': 'Invalid step'}, status=400)
            except (DepartmentTeams.DoesNotExist, Employee.DoesNotExist, ValueError) as e:
                logger.error(f"Error in CreateDataView: {str(e)}")
                return JsonResponse({'error': 'Invalid data'}, status=400)
        return JsonResponse({'error': 'Invalid request'}, status=400)

class DeleteDataView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        return view

    def delete(self, request, table, id):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                if table == 'employee':
                    employee = Employee.objects.filter(
                        emp_id=id,
                        department_team__company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
                    ).first()
                    if not employee:
                        return JsonResponse({'error': 'Invalid employee'}, status=400)
                    employee.delete()
                    logger.debug(f"Employee deleted: {id}")
                    return JsonResponse({'message': 'Employee deleted successfully'})
                return JsonResponse({'error': 'Invalid table'}, status=400)
            except (Employee.DoesNotExist, ValueError):
                return JsonResponse({'error': 'Invalid data'}, status=400)
        return JsonResponse({'error': 'Invalid request'}, status=400)


class DepartmentGroupsSectionsView(View):
    def get(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = DepartmentGroupsSerializer(DepartmentGroups.objects.all(), many=True).data
            print(data)
            return JsonResponse({'data': data})
        return JsonResponse({'error': 'Invalid request'}, status=400)


class DesignationsView(View):
    def get(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            company_id = request.GET.get('company_id')
            if not company_id:
                return JsonResponse({'error': 'company_id required'}, status=400)
            print(company_id)
            data = DesignationSerializer(Designation.objects.filter(company_id=company_id), many=True).data
            return JsonResponse({'data': data})
        return JsonResponse({'error': 'Invalid request'}, status=400)


class DesignationCreateView(View):
    def post(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = json.loads(request.body)
            serializer = DesignationCreateSerializer(data=data)
            if serializer.is_valid():
                designation = serializer.save()
                return JsonResponse({'id': designation.id, 'title': designation.title})
            return JsonResponse({'error': serializer.errors}, status=400)
        return JsonResponse({'error': 'Invalid request'}, status=400)
    

class LocationsView(View):
    def get(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            locations = Location.objects.all()
            if locations.exists():
                data = LocationsSerializer(locations, many=True).data
            else:
                data = []
            return JsonResponse({'data': data})
        return JsonResponse({'error': 'Invalid request'}, status=400)







# class LoginView(View):
#     template_name = "login.html"

#     def get(self, request):
#         """Handles GET requests and renders the login form."""
#         return render(request, self.template_name)

#     def post(self, request):
#         """Handles POST requests and authenticates only superusers."""
#         email = request.POST.get("email")
#         password = request.POST.get("password")

#         user = authenticate(username=email, password=password)
#         if user is not None:
#             if user.is_active and user.is_superuser:  # ✅ check superuser
#                 login(request, user)
#                 return redirect("dashboard")  # Replace with your dashboard URL
#             elif not user.is_active:
#                 messages.error(request, "Your account is disabled.")
#             else:
#                 messages.error(request, "You are not authorized to access this panel.")
#         else:
#             messages.error(request, "Invalid email or password.")

#         return render(request, self.template_name)












# class DashboardView(View):
#     template_name = "dashboard.html"

#     def get(self, request):
#         if not request.user.is_authenticated or not request.user.is_superuser:
#             return redirect("login")

#         companies = Company.objects.filter(is_deleted=False).order_by("name")
#         hr_users = CustomUser.objects.filter(
#             is_deleted=False,
#             is_staff=True,
#             is_superuser=False
#         ).order_by("full_name")

#         return render(request, self.template_name, {
#             "companies": companies,
#             "hr_users": hr_users
#         })


# class AddCompanyView(View):
#     template_name = "add_company.html"

#     def get(self, request):
#         form = CompanyForm()
#         return render(request, self.template_name, {"form": form})

#     def post(self, request):
#         form = CompanyForm(request.POST)
#         if form.is_valid():
#             form.save()
#             messages.success(request, "Company added successfully!")
#             return redirect("dashboard")
#         return render(request, self.template_name, {"form": form})
    

# class EditCompanyView(View):
#     template_name = "edit_company.html"

#     def get(self, request, pk):
#         company = get_object_or_404(Company, pk=pk, is_deleted=False)
#         form = CompanyForm(instance=company)
#         return render(request, self.template_name, {"form": form, "company": company})

#     def post(self, request, pk):
#         company = get_object_or_404(Company, pk=pk, is_deleted=False)
#         form = CompanyForm(request.POST, instance=company)
#         if form.is_valid():
#             form.save()
#             messages.success(request, "Company updated successfully!")
#             return redirect("dashboard")
#         return render(request, self.template_name, {"form": form, "company": company})


# class DeleteCompanyView(View):
#     def get(self, request, pk):
#         company = get_object_or_404(Company, pk=pk)
#         company.is_deleted = True  # soft delete
#         company.save()
#         messages.success(request, "Company deleted successfully ")
#         return redirect("dashboard")



# # --- CREATE HR ---
# class AddHRView(View):
#     template_name = "add_hr.html"

#     def get(self, request):
#         form = CustomUserForm()
#         return render(request, self.template_name, {"form": form})

#     def post(self, request):
#         form = CustomUserForm(request.POST)
#         if form.is_valid():
#             hr = form.save(commit=False)
#             hr.is_staff = True
#             # Make sure HR is not admin/superuser
#             hr.is_superuser = False
#             hr.save()
#             messages.success(request, "HR user added successfully!")
#             return redirect("dashboard")
#         return render(request, self.template_name, {"form": form})


# # --- UPDATE HR ---
# class EditHRView(View):
#     template_name = "edit_hr.html"

#     def get(self, request, pk):
#         hr = get_object_or_404(
#             CustomUser,
#             pk=pk,
#             is_deleted=False,
#             is_staff=True,
#             is_superuser=False,   # exclude superuser
#         )

#         print("Editing HR:", hr)

#         form = CustomUserUpdateForm(instance=hr)
#         return render(request, self.template_name, {"form": form, "hr": hr})

#     def post(self, request, pk):
#         hr = get_object_or_404(
#             CustomUser,
#             pk=pk,
#             is_deleted=False,
#             is_staff=True,
#             is_superuser=False,
#         )

#         print("Updating HR:", hr)

#         form = CustomUserUpdateForm(request.POST, instance=hr)
#         if form.is_valid():
#             hr = form.save(commit=False)
#             hr.is_staff = True
#             hr.is_superuser = False
#             hr.save()
#             messages.success(request, "HR user updated successfully!")
#             return redirect("dashboard")
        
#         else:
#             print("Form errors:", form.errors)   # 👈 add this
#             return render(request, self.template_name, {"form": form, "hr": hr})


# # --- DELETE HR (soft delete) ---
# class DeleteHRView(View):
#     def get(self, request, pk):
#         hr = get_object_or_404(
#             CustomUser,
#             pk=pk,
#             is_staff=True,
#             is_superuser=False,  # don’t delete superuser
#         )
#         hr.is_deleted = True   # soft delete
#         hr.save()
#         messages.success(request, "HR user deleted successfully")
#         return redirect("dashboard")





















