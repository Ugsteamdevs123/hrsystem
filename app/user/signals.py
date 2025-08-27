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
        

        # target_models = [ProposedPackageDetails, FinancialImpactPerMonth, IncrementDetailsSummary]

        # Determine context
        employee = getattr(instance, 'employee', None)
        company = getattr(instance, 'company', None) or (employee.company if employee else None)
        department_team = getattr(instance, 'department_team', None) or (employee.department_team if employee else None)

        # Get all formulas for the company
        formulas = FieldFormula.objects.filter(company=company).select_related('formula')

        # Prioritize employee-specific formulas
        employee_formulas = formulas.filter(employee=employee, department_team=department_team) if employee else formulas.none()
        print("employee_formulas: ", employee_formulas)
        department_formulas = formulas.filter(employee__isnull=True, department_team=department_team)
        print("department_formulas: ", department_formulas)
        # Combine, prioritizing employee formulas
        formula_ids = list(employee_formulas.values_list('id', flat=True))
        formula_ids += list(department_formulas.exclude(id__in=employee_formulas).values_list('id', flat=True))
        print("formula_ids: ", formula_ids)
        formulas = FieldFormula.objects.filter(id__in=formula_ids).select_related('formula')

        if not formulas:
            print(f"No formulas found for company={company}, department_team={department_team}, employee={employee}")
            return

        # Topological sort with context
        ordered = topological_sort(formulas, company=company, employee=employee, department_team=department_team)
        print("ordered: ", ordered)

        for model_name, field in ordered:
            print("model_name, field: ", model_name, field)
            # Prefer employee-specific formula, else department-specific
            field_formula = employee_formulas.filter(target_model=model_name, target_field=field).first() or \
                           department_formulas.filter(target_model=model_name, target_field=field).first()
            if not field_formula:
                print(f"No formula found for {model_name}.{field}")
                continue

            # Choose instance
            if model_name == "IncrementDetailsSummary":
                target_instance = IncrementDetailsSummary.objects.filter(
                    company=company,
                    department_team=department_team
                ).first()
            else:
                instance.refresh_from_db()
                target_instance = instance

            if not target_instance:
                print(f"No instance found for {model_name} with company={company}, department_team={department_team}")
                continue

            expression = field_formula.formula.formula_expression
            try:
                value = evaluate_formula(target_instance, expression, model_name)
                print("model_name: ", model_name, "  :::  field: ", field, "  :::  value: ", value)
                Model = apps.get_model('user', model_name)
                Model.objects.filter(id=target_instance.id).update(**{field: value})
            except ValueError as e:
                print(f"Error evaluating formula for {model_name}.{field}: {e}")

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