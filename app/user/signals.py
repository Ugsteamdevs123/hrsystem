import logging

from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver
from django.utils import timezone

from .utils import update_department_team_increment_summary
from .models import CurrentPackageDetails, ProposedPackageDetails, FinancialImpactPerMonth, IncrementDetailsSummary, DepartmentTeams

logger = logging.getLogger(__name__)


@receiver(post_save, sender=CurrentPackageDetails)
@receiver(post_save, sender=ProposedPackageDetails)
@receiver(post_save, sender=FinancialImpactPerMonth)
def update_increment_summary(sender, instance, created, **kwargs):
    """
    Signal to check the driver wallet amount when a DriverAdditional is saved.
    """
    try:
        increment_details_summary = IncrementDetailsSummary.objects.filter(company = instance.employee.company, department_team = instance.employee.department_team)

        if not increment_details_summary.exists():
            IncrementDetailsSummary.objects.create(company = instance.employee.company, department_team = instance.employee.department_team)

        update_department_team_increment_summary(sender, instance, instance.employee.company, instance.employee.department_team)

    except Exception as e:
        print(f"Error in updating increment summary: {e}")
        # logger.error(f"Error in checking driver wallet balance: {e}", extra={'id': instance.id})


@receiver(post_save,sender=DepartmentTeams)
def add_new_increment_details_summary_record(sender, instance, created, **kwargs):
    """
    Signal to check the driver wallet amount when a DriverAdditional is saved.
    """
    try:
        if created:
            IncrementDetailsSummary.objects.create(company = instance.company, department_team = instance)

    except Exception as e:
        print(f"Error in adding new increment details summary record: {e}")
        # logger.error(f"Error in checking driver wallet balance: {e}", extra={'id': instance.id})


# @receiver(post_save, sender=CurrentPackageDetails)
# @receiver(post_save, sender=ProposedPackageDetails)
# @receiver(post_save, sender=FinancialImpactPerMonth)
# def update_formula_fields(sender, instance, **kwargs):
#     """Update formula-based fields when related models are saved."""
#     employee = instance.employee
#     for model in [ProposedPackageDetails, FinancialImpactPerMonth]:
#         try:
#             obj = model.objects.get(employee=employee)
#             for field in obj._meta.get_fields():
#                 if isinstance(field, models.ForeignKey) and field.related_model == Formula:
#                     formula = getattr(obj, field.name)
#                     if formula:
#                         value = formula.evaluate(employee)
#                         setattr(obj, f"{field.name}_value", value)
#             obj.save()
#         except model.DoesNotExist:
#             pass