import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps

from .utils import update_department_team_increment_summary, topological_sort, evaluate_formula
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
        

        target_models = [ProposedPackageDetails, FinancialImpactPerMonth, IncrementDetailsSummary]
        
        
        # _, model_cls = get_model_by_name(target_model.__name__)
        # print("model_cls: ", model_cls)
        # fields = list_fields(model_cls)
        # print("fields: ", fields)

        # graph, indegree = build_dependency_graph(FieldFormula.objects.all())
        ordered = topological_sort(FieldFormula.objects.all())

        print("ordered: ", ordered)
        for model_name, field in ordered:
            print("model_name, field: ", model_name, field)
            field_formula = FieldFormula.objects.filter(target_model=model_name, target_field=field)
            print("field_formula", field_formula)
            # field_formula = FieldFormula.objects.filter(target_model=target_model.__name__, target_field=field)
            # if not field_formula.exists():
            #     continue
            
            # choose instance depending on model
            if model_name == "IncrementDetailsSummary":
                target_instance = IncrementDetailsSummary.objects.filter(
                    company=instance.employee.company,
                    department_team=instance.employee.department_team
                ).first()
            else:
                instance.refresh_from_db()
                target_instance = instance

            field_formula = field_formula.first()
            expression = field_formula.formula.formula_expression
            # value = evaluate_formula(target_instance, expression, target_model.__name__)
            value = evaluate_formula(target_instance, expression, model_name)
            
            print("model_name: ", model_name, "  :::  field: ", field, "  :::  value: ", value, '\n')

            # **{field: value} upacks them and the 'field' is replaced by its value. e.g., 'gross_salary' and value is will be value e.g., '12'
            # .update saves without signals recursion
            Model = apps.get_model('user', model_name)
            Model.objects.filter(id = target_instance.id).update(**{field: value})

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