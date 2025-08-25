import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .utils import update_department_team_increment_summary, iter_allowed_models, get_model_by_name, list_fields, evaluate_formula
from .models import CurrentPackageDetails, ProposedPackageDetails, FinancialImpactPerMonth, IncrementDetailsSummary, DepartmentTeams, FieldFormula

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
        instance.refresh_from_db()
        
        if sender is ProposedPackageDetails:
            target_models = ['ProposedPackageDetails', 'IncrementDetailsSummary']
        elif sender is FinancialImpactPerMonth:
            target_models = ['FinancialImpactPerMonth', 'IncrementDetailsSummary']
        else:
            target_models = ['IncrementDetailsSummary']
        
        
        for target_model in target_models:
            _, model_cls = get_model_by_name(target_model)
            print("model_cls: ", model_cls)
            fields = list_fields(model_cls)
            print("fields: ", fields)
            for field in fields:
                field_formula = FieldFormula.objects.filter(target_model=target_model, target_field=field)
                if not field_formula.exists():
                    continue

                field_formula = field_formula.first()
                expression = field_formula.formula.formula_expression
                value = evaluate_formula(instance, expression)
                # setattr(instance, field, value)
                print("field: ", field, "  :::  value: ", value, '\n')

                # **{field: value} upacks them and the 'field' is replaced by its value. e.g., 'gross_salary' and value is will be value e.g., '12'
                sender.objects.filter(id = instance.id).update(**{field: value})
                instance.refresh_from_db()
                # instance.save(update_fields=[field])  # Save without recursion

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



    



# from .utils import evaluate_formula

# @receiver(post_save, sender=ProposedPackageDetails)
# def compute_proposed_package(sender, instance, **kwargs):
#     target_model = 'ProposedPackageDetails'
#     for field in ['increased_amount', 'revised_salary', 'revised_fuel_allowance']:  # Add others as needed
#         try:
#             field_formula = FieldFormula.objects.get(target_model=target_model, target_field=field)
#             expression = field_formula.formula.formula_expression
#             value = evaluate_formula(instance, expression)
#             setattr(instance, field, value)
#             instance.save(update_fields=[field])  # Save without recursion
#         except FieldFormula.DoesNotExist:
#             pass  # No formula, skip

# @receiver(post_save, sender=FinancialImpactPerMonth)
# def compute_financial_impact(sender, instance, **kwargs):
#     target_model = 'FinancialImpactPerMonth'
#     for field in ['gratuity', 'bonus', 'leave_encashment', 'mobile_allowance', 'total']:  # Add others
#         try:
#             field_formula = FieldFormula.objects.get(target_model=target_model, target_field=field)
#             expression = field_formula.formula.formula_expression
#             value = evaluate_formula(instance, expression)
#             setattr(instance, field, value)
#             instance.save(update_fields=[field])
#         except FieldFormula.DoesNotExist:
#             pass