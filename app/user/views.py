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

from .models import hr_assigned_companies, DepartmentTeams, IncrementDetailsSummary, Company

from .serializer import IncrementDetailsSummarySerializer

from collections import defaultdict
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
        return view
    
    def get(self, request):
        # Fetch companies assigned to the logged-in HR
        assigned_companies = hr_assigned_companies.objects.filter(hr=request.user)
        company_data = [
            {'company_id': ac.company.id, 'company_name': ac.company.name}
            for ac in assigned_companies
        ]

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
                summary_id = request.POST.get('id')
                eligible_for_increment = request.POST.get('eligible_for_increment')
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
        return render(request, 'department_team.html')

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
                print(data)
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
            assigned_companies = (
                hr_assigned_companies.objects
                .filter(hr=request.user)
                .select_related("company")
                .prefetch_related(
                    Prefetch(
                        "company__departmentteams_set",  # reverse relation from Company → DepartmentTeams
                        queryset=DepartmentTeams.objects.all(),
                        to_attr="prefetched_departments"
                    )
                )
            )

            data = [
                {
                    "company_id": ac.company.id,
                    "company": ac.company.name,
                    "departments": [
                        {"id": dept.id, "name": dept.name}
                        for dept in getattr(ac.company, "prefetched_departments", [])
                    ]
                }
                for ac in assigned_companies
            ]
            # return data

            return JsonResponse({'data': data})  # Return companies for add_department.html
        except Exception as e:
            print(e)
