from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render


# class IsSuperUser(BasePermission):
#     message = 'You Must Be SuperUser'

#     def has_permission(self, request, view):
#         return bool(
#             request.user.is_authenticated and request.user.is_superuser
#         )


# class IsSuperUserOrReadOnly(BasePermission):
    
#     def has_permission(self, request, view):
#         if request.method in SAFE_METHODS:
#             return True

#         return bool(
#             request.user.is_authenticated and request.user.is_superuser
#         )


# class IsSuperUserOrAuthor(BasePermission):
#     message = 'You Must Be SuperUser or Author'

#     def has_permission(self, request, view):
#         return bool(
#             request.user.is_authenticated and request.user.is_superuser or
#             request.user.is_authenticated and request.user.author
#         )


# class IsSuperUserOrAuthorOrReadOnly(BasePermission):

#     def has_object_permission(self, request, view, obj):
#         if request.method in SAFE_METHODS:
#             return True

#         return bool(
#             request.user.is_authenticated and request.user.is_superuser or
#             request.user.is_authenticated and obj.author == request.user 
#         )
    
# class IsInCustomerServiceGroup(BasePermission):
#     """
#     Allows access only to users in the 'Customer Service' group.
#     """
#     def has_permission(self, request, view):
#         group_name = 'Customer Service'
#         return request.user.is_authenticated and request.user.groups.filter(name=group_name).exists()


# class IsCustomerServiceOrAdmin(BasePermission):
#     message = 'You Must Be Customer Service or Admin'

#     def has_permission(self, request, view):
#         group_name = 'Customer Service'
#         return bool(
#             request.user.is_authenticated and request.user.groups.filter(name=group_name).exists() or
#             request.user.is_authenticated and request.user.is_superuser
#         )

# class IsMarketingManagerOrAdmin(BasePermission):
#     message = 'You Must Be Marketing Manager or Admin'

#     def has_permission(self, request, view):
#         group_name = 'marketing manager'
#         return bool(
#             request.user.is_authenticated and request.user.groups.filter(name=group_name).exists() or
#             request.user.is_authenticated and request.user.is_superuser
#         )

# class IsInMarketingGroup(BasePermission):
#     """
#     Allows access only to users in the 'marketing' group.
#     """
#     def has_permission(self, request, view):
#         group_name = 'marketing'
#         return request.user.is_authenticated and request.user.groups.filter(name=group_name).exists()


# class IsDriverManagementMemberOrAdmin(BasePermission):
#     message = 'You Must Be driver management member or Admin'

#     def has_permission(self, request, view):
#         group_name = 'driver management member'
#         return bool(
#             request.user.is_authenticated and request.user.groups.filter(name=group_name).exists() or
#             request.user.is_authenticated and request.user.is_superuser
#         )
    


class GroupOrSuperuserPermission:
    """
    Permission class to check if user is superuser or belongs to a specific group.
    """
    group_name = None  # Must be set when instantiating

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.is_superuser or request.user.groups.filter(name=self.group_name).exists():
            return True
        return HttpResponseForbidden(f'You Must Be {self.group_name} or Admin')


class PermissionRequiredMixin:
    """
    Mixin to process a list of permission classes, similar to DRF's permission_classes.
    """
    permission_classes = []

    def dispatch(self, request, *args, **kwargs):
        for permission_class in self.permission_classes:
            # Instantiate permission class and set group_name if needed
            permission = permission_class()
            if hasattr(self, 'group_name') and hasattr(permission, 'group_name'):
                permission.group_name = self.group_name
            result = permission.has_permission(request, self)
            if result is not True:
                return result  # Return redirect or forbidden response
        return super().dispatch(request, *args, **kwargs)