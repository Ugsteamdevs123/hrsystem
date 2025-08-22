from venv import logger
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.messages import success as messages_success
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import View

# from django.views import View
from django.core.exceptions import ObjectDoesNotExist

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
    Location,
    EmployeeStatus,
    Formula)

from .utils import get_companies_and_department_teams
from .serializer import (
    IncrementDetailsSummarySerializer,
    DepartmentGroupsSerializer,
    DesignationSerializer,
    DesignationCreateSerializer,
    LocationsSerializer,
    EmployeeStatusSerializer
)

import json

# # Original function-based decorator (kept for reference)
# def group_or_superuser_required(group_name):
#     def decorator(view_func):
#         def wrapper(request, *args, **kwargs):
#             if not request.user.is_authenticated:
#                 return redirect('login')
#             if request.user.is_superuser or request.user.groups.filter(name=group_name).exists():
#                 return view_func(request, *args, **kwargs)
#             return HttpResponseForbidden(f'You Must Be {group_name} or Admin')
#         return wrapper
#     return decorator

# Class-based mixin equivalent
# class GroupOrSuperuserRequiredMixin:
#     """
#     Mixin to restrict access to users who are either superusers or belong to a specific group.
#     """
#     group_name = None  # Must be set in the view

#     def dispatch(self, request, *args, **kwargs):
#         if not request.user.is_authenticated:
#             return redirect('login')
#         if request.user.is_superuser or request.user.groups.filter(name=self.group_name).exists():
#             return super().dispatch(request, *args, **kwargs)
#         return HttpResponseForbidden(f'You Must Be {self.group_name} or Admin')

# # Example usage with the CustomerServiceLogoutView
# class CustomerServiceLogoutView(View):
#     permission_classes = [GroupOrSuperuserRequiredMixin]
#     """
#     Class-based logout view for customer service representatives.
#     Handles POST requests to log out the user, clear sessions, and redirect to the login page.
#     Renders a confirmation page for GET requests.
#     """
#     group_name = 'Customer Service'  # Set the group name for the mixin

#     @classmethod
#     def as_view(cls, **initkwargs):
#         view = super().as_view(**initkwargs)
#         view = login_required(view)
#         view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
#         view = csrf_protect(view)
#         return view

#     def post(self, request):
#         user = request.user
#         token = request.session.get('access_token', '')  # Optional: Retrieve JWT token from session
#         Session.objects.filter(user=user).delete()  # Clear active session
#         user.logged = False
#         user.save()
#         logout(request)  # Clear Django session
#         messages_success(request, 'You have been logged out successfully.')
#         return redirect('login')

#     def get(self, request):
#         return render(request, 'logout.html')



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
        # assigned_companies = hr_assigned_companies.objects.filter(hr=request.user)
        # company_data = [
        #     {'company_id': ac.company.id, 'company_name': ac.company.name}
        #     for ac in assigned_companies
        # ]

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
        # assigned_companies = hr_assigned_companies.objects.filter(hr=request.user)
        # company_data = [
        #     {'company_id': ac.company.id, 'company_name': ac.company.name}
        #     for ac in assigned_companies
        # ]

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



# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx


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
                'emp_status': financial_impact.emp_status.status if financial_impact and financial_impact.emp_status else '',
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
                table_html += f'<td><button class="btn btn-sm btn-primary edit-employee-btn" onclick="console.log(\'Edit button clicked for employee: {row["employee_id"]}\')">Edit</button> <button class="btn btn-sm btn-danger delete-employee-btn" onclick="console.log(\'Delete button clicked for employee: {row["employee_id"]}\')">Delete</button></td>'
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
                        # increased_amount_id=request.POST.get('increased_amount_id'),
                        # revised_salary_id=request.POST.get('revised_salary_id'),
                        increased_fuel_amount=request.POST.get('increased_fuel_amount'),
                        # revised_fuel_allowance_id=request.POST.get('revised_fuel_allowance_id'),
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
                        # serving_years=request.POST.get('serving_years'),
                        # salary=request.POST.get('salary'),
                        # gratuity_id=request.POST.get('gratuity_id'),
                        # bonus_id=request.POST.get('bonus_id'),
                        # leave_encashment_id=request.POST.get('leave_encashment_id'),
                        # mobile_allowance_id=request.POST.get('mobile_allowance_id'),
                        # fuel=request.POST.get('fuel'),
                        # total_id=request.POST.get('total_id')
                    )
                    logger.debug(f"FinancialImpactPerMonth created for employee: {employee_id}")
                    return JsonResponse({'message': 'Financial Impact created'})
                return JsonResponse({'error': 'Invalid step'}, status=400)
            except (DepartmentTeams.DoesNotExist, Employee.DoesNotExist, ValueError) as e:
                logger.error(f"Error in CreateDataView: {str(e)}")
                return JsonResponse({'error': 'Invalid data'}, status=400)
        return JsonResponse({'error': 'Invalid request'}, status=400)


class GetDataView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        return view

    def get(self, request, table, id):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                if table == 'employee':
                    logger.debug(f"Fetching employee with emp_id: {id}")
                    employee = Employee.objects.filter(
                        emp_id=id,
                        department_team__company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
                    ).first()
                    if not employee:
                        logger.error(f"Employee with emp_id {id} not found or not authorized")
                        return JsonResponse({'error': f'Employee with ID {id} not found'}, status=404)
                    current_package = CurrentPackageDetails.objects.filter(employee=employee).first() or {}
                    proposed_package = ProposedPackageDetails.objects.filter(employee=employee).first() or {}
                    financial_impact = FinancialImpactPerMonth.objects.filter(employee=employee).first() or {}
                    data = {
                        'employee': {
                            'fullname': employee.fullname,
                            'department_group_id': employee.department_group_id,
                            'section_id': employee.section_id,
                            'designation_id': employee.designation_id,
                            'location_id': employee.location_id,
                            'date_of_joining': employee.date_of_joining.isoformat() if employee.date_of_joining else '',
                            'resign': employee.resign,
                            'date_of_resignation': employee.date_of_resignation.isoformat() if employee.date_of_resignation else '',
                            'remarks': employee.remarks or '',
                            'image': employee.image.url if employee.image else ''
                        },
                        'current_package': {
                            'gross_salary': str(current_package.gross_salary) if current_package and current_package.gross_salary else '',
                            'vehicle': current_package.vehicle if current_package else '',
                            'fuel_limit': str(current_package.fuel_limit) if current_package and current_package.fuel_limit else '',
                            'mobile_allowance': str(current_package.mobile_allowance) if current_package and current_package.mobile_allowance else ''
                        },
                        'proposed_package': {
                            'increment_percentage': str(proposed_package.increment_percentage) if proposed_package and proposed_package.increment_percentage else '',
                            'increased_amount_id': str(proposed_package.increased_amount_id) if proposed_package and proposed_package.increased_amount_id else '',
                            'revised_salary_id': str(proposed_package.revised_salary_id) if proposed_package and proposed_package.revised_salary_id else '',
                            'increased_fuel_amount': str(proposed_package.increased_fuel_amount) if proposed_package and proposed_package.increased_fuel_amount else '',
                            'revised_fuel_allowance_id': str(proposed_package.revised_fuel_allowance_id) if proposed_package and proposed_package.revised_fuel_allowance_id else '',
                            'mobile_allowance': str(proposed_package.mobile_allowance) if proposed_package and proposed_package.mobile_allowance else '',
                            'vehicle': proposed_package.vehicle if proposed_package else ''
                        },
                        'financial_impact': {
                            'emp_status_id': str(financial_impact.emp_status_id) if financial_impact and financial_impact.emp_status_id else '',
                            'serving_years': str(financial_impact.serving_years) if financial_impact and financial_impact.serving_years else '',
                            'salary': str(financial_impact.salary) if financial_impact and financial_impact.salary else '',
                            'gratuity_id': str(financial_impact.gratuity_id) if financial_impact and financial_impact.gratuity_id else '',
                            'bonus_id': str(financial_impact.bonus_id) if financial_impact and financial_impact.bonus_id else '',
                            'leave_encashment_id': str(financial_impact.leave_encashment_id) if financial_impact and financial_impact.leave_encashment_id else '',
                            'mobile_allowance_id': str(financial_impact.mobile_allowance_id) if financial_impact and financial_impact.mobile_allowance_id else '',
                            'fuel': str(financial_impact.fuel) if financial_impact and financial_impact.fuel else '',
                            'total_id': str(financial_impact.total_id) if financial_impact and financial_impact.total_id else ''
                        }
                    }
                    logger.debug(f"Fetched data for employee {id}: {data}")
                    return JsonResponse({'data': data})
                return JsonResponse({'error': 'Invalid table'}, status=400)
            except (Employee.DoesNotExist, ValueError) as e:
                logger.error(f"Error fetching employee {id}: {str(e)}")
                return JsonResponse({'error': f'Invalid data: {str(e)}'}, status=400)
        return JsonResponse({'error': 'Invalid request'}, status=400)
    

class UpdateDataView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = login_required(view)
        view = cache_control(no_cache=True, must_revalidate=True, no_store=True)(view)
        view = ensure_csrf_cookie(view)
        return view

    def patch(self, request, department_id):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                data = json.loads(request.body)
                print(data)
                step = data.get('step')
                employee_id = data.get('employee_id')
                department = DepartmentTeams.objects.get(
                    id=department_id,
                    company__in=hr_assigned_companies.objects.filter(hr=request.user).values('company')
                )
                employee = Employee.objects.get(emp_id=employee_id, department_team=department)
                if step == 'employee':
                    employee.fullname = data.get('fullname')
                    employee.department_group_id = data.get('department_group_id')
                    employee.section_id = data.get('section_id')
                    employee.designation_id = data.get('designation_id')
                    employee.location_id = data.get('location_id')
                    employee.date_of_joining = data.get('date_of_joining')
                    employee.resign = data.get('resign') == 'true'
                    employee.date_of_resignation = data.get('date_of_resignation') or None
                    employee.remarks = data.get('remarks') or ''
                    if 'image' in request.FILES:
                        employee.image = request.FILES.get('image')
                    employee.save()
                    logger.debug(f"Employee updated: {employee_id}")
                    return JsonResponse({'message': 'Employee updated', 'employee_id': employee_id})
                elif step == 'current_package':
                    current_package, created = CurrentPackageDetails.objects.get_or_create(employee=employee)
                    current_package.gross_salary = data.get('gross_salary')
                    current_package.vehicle = data.get('vehicle')
                    current_package.fuel_limit = data.get('fuel_limit', None)
                    current_package.mobile_allowance = data.get('mobile_allowance', None)
                    current_package.save()
                    logger.debug(f"CurrentPackageDetails updated for employee: {employee_id}")
                    return JsonResponse({'message': 'Current Package updated'})
                elif step == 'proposed_package':
                    proposed_package, created = ProposedPackageDetails.objects.get_or_create(employee=employee)
                    proposed_package.increment_percentage = data.get('increment_percentage')
                    # proposed_package.increased_amount_id = data.get('increased_amount_id')
                    # proposed_package.revised_salary_id = data.get('revised_salary_id')
                    proposed_package.increased_fuel_amount = data.get('increased_fuel_amount')
                    # proposed_package.revised_fuel_allowance_id = data.get('revised_fuel_allowance_id')
                    proposed_package.mobile_allowance = data.get('mobile_allowance')
                    proposed_package.vehicle = data.get('vehicle')
                    proposed_package.save()
                    logger.debug(f"ProposedPackageDetails updated for employee: {employee_id}")
                    return JsonResponse({'message': 'Proposed Package updated'})
                elif step == 'financial_impact':
                    financial_impact, created = FinancialImpactPerMonth.objects.get_or_create(employee=employee)
                    financial_impact.emp_status_id = data.get('emp_status_id')
                    # financial_impact.serving_years = data.get('serving_years')
                    # financial_impact.salary = data.get('salary')
                    # financial_impact.gratuity_id = data.get('gratuity_id')
                    # financial_impact.bonus_id = data.get('bonus_id')
                    # financial_impact.leave_encashment_id = data.get('leave_encashment_id')
                    # financial_impact.mobile_allowance_id = data.get('mobile_allowance_id')
                    # financial_impact.fuel = data.get('fuel')
                    # financial_impact.total_id = data.get('total_id')
                    financial_impact.save()
                    logger.debug(f"FinancialImpactPerMonth updated for employee: {employee_id}")
                    return JsonResponse({'message': 'Financial Impact updated'})
                return JsonResponse({'error': 'Invalid step'}, status=400)
            except (DepartmentTeams.DoesNotExist, Employee.DoesNotExist, ValueError) as e:
                logger.error(f"Error in UpdateDataView: {str(e)}")
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


class EmployeeStatusView(View):
    def get(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            employee_status = EmployeeStatus.objects.all()
            
            if employee_status.exists():
                data = EmployeeStatusSerializer(EmployeeStatus.objects.all(), many=True).data
                return JsonResponse({'data': data})
            
            return JsonResponse({'data': []})
        
        return JsonResponse({'error': 'Invalid request'}, status=400)
    






# In app/views.py
from django.shortcuts import render, redirect
from .models import FieldFormula, Formula, FieldReference
from .forms import FieldFormulaForm, FormulaForm

def manage_formulas(request):
    field_formulas = FieldFormula.objects.all()
    field_references = FieldReference.objects.all()
    if request.method == 'POST':
        form = FieldFormulaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('user:manage_formulas')
    else:
        form = FieldFormulaForm()
    return render(request, 'manage_formulas.html', {
        'form': form,
        'field_formulas': field_formulas,
        'field_references': field_references
    })

def create_formula(request):
    if request.method == 'POST':
        form = FormulaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('user:manage_formulas')
    else:
        form = FormulaForm()
    return render(request, 'create_formula.html', {'form': form})