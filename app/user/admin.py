from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .import models
from django.utils.translation import gettext_lazy as _
from .forms import FieldReferenceAdminForm
from django.urls import path
from django.http import JsonResponse
from .forms import get_model_by_name, list_fields

# Register your models here.



@admin.register(models.Gender)
class GenderAdmin(admin.ModelAdmin):
    list_display = ("id", "gender")
    search_fields = ("gender",)


@admin.register(models.CustomUser)
class CustomUserAdmin(UserAdmin):
    # Fields to display in the admin list view
    list_display = ("email", "full_name", "gender", "contact", "is_staff", "is_active" , "is_deleted" , "first_time_login_to_reset_pass")
    list_filter = ("is_staff", "is_active", "gender", "groups")

    # Fieldsets for editing users
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("full_name", "gender", "contact" , "is_deleted" , "first_time_login_to_reset_pass")}),
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


@admin.register(models.FieldReference)
class FieldReferenceAdmin(admin.ModelAdmin):
    form = FieldReferenceAdminForm
    list_display = ("model_name", "field_name", "display_name", "path")

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "get-fields/",
                self.admin_site.admin_view(self.get_fields_view),
                name="fieldreference_get_fields",
            ),
        ]
        return custom + urls

    def get_fields_view(self, request):
        model_name = request.GET.get("model")
        _, model_cls = get_model_by_name(model_name)
        fields = list_fields(model_cls)
        # Return as [["value","label"], ...]
        return JsonResponse([[f, f] for f in fields], safe=False)

    class Media:
        # No template override needed; admin will auto-include this JS
        js = ("admin/js/fieldreference.js",)
    

admin.site.register(models.Location)
admin.site.register(models.IncrementDetailsSummary)
admin.site.register(models.hr_assigned_companies)
admin.site.register(models.Company)
admin.site.register(models.Designation)
admin.site.register(models.DepartmentTeams)
admin.site.register(models.DepartmentGroups)
admin.site.register(models.Section)
admin.site.register(models.EmployeeStatus)
admin.site.register(models.CurrentPackageDetails)
admin.site.register(models.ProposedPackageDetails)
admin.site.register(models.FinancialImpactPerMonth)
admin.site.register(models.DynamicAttributeDefinition)
admin.site.register(models.DynamicAttribute)
admin.site.register(models.Formula)
admin.site.register(models.FieldFormula)
admin.site.register(models.Configurations)
admin.site.register(models.SummaryStatus)
admin.site.register(models.Employee)


# admin.site.register(models.VehicleInfo)

admin.site.register(models.VehicleBrand)
admin.site.register(models.VehicleModel)


admin.site.register(models.EmployeeDraft)
admin.site.register(models.CurrentPackageDetailsDraft)
admin.site.register(models.ProposedPackageDetailsDraft)
admin.site.register(models.FinancialImpactPerMonthDraft)


# admin.site.register(models.VehicleOwnerShipModel)

