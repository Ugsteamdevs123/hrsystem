from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .import models
from django.utils.translation import gettext_lazy as _

# Register your models here.



@admin.register(models.Gender)
class GenderAdmin(admin.ModelAdmin):
    list_display = ("id", "gender")
    search_fields = ("gender",)


@admin.register(models.CustomUser)
class CustomUserAdmin(UserAdmin):
    # Fields to display in the admin list view
    list_display = ("email", "full_name", "gender", "contact", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active", "gender", "groups")

    # Fieldsets for editing users
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("full_name", "gender", "contact")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login",)}),
    )

    # Fieldsets when creating a user
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "gender", "contact", "password1", "password2", "is_staff", "is_active"),
        }),
    )

    search_fields = ("email", "full_name", "contact")
    ordering = ("email",)














admin.site.register(models.Designation)
admin.site.register(models.DepartmentTeams)
admin.site.register(models.DepartmentGroups)
admin.site.register(models.Section)
admin.site.register(models.Company)
admin.site.register(models.EmployeeStatus)
admin.site.register(models.CurrentPackageDetails)
admin.site.register(models.ProposedPackageDetails)
admin.site.register(models.FinancialImpactPerMonth)
