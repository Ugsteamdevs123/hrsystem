import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps

from .utils import update_department_team_increment_summary, topological_sort, evaluate_formula
from .models import SummaryStatus, CurrentPackageDetails, ProposedPackageDetails, FinancialImpactPerMonth, IncrementDetailsSummary, DepartmentTeams, FieldFormula, CurrentPackageDetailsDraft, ProposedPackageDetailsDraft, FinancialImpactPerMonthDraft, IncrementDetailsSummaryDraft

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
        # formulas = FieldFormula.objects.filter(company=company).select_related('formula')
        formulas = FieldFormula.objects.exclude(target_model__endswith='Draft').select_related('formula')

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
        print("formulas: ", formulas)

        if not formulas:
            print(f"No formulas found for company={company}, department_team={department_team}, employee={employee}")
            return

        # Topological sort with context
        print(formulas)
        ordered = topological_sort(formulas, company=company, employee=employee, department_team=department_team)
        print("ordered: ", ordered)

        for model_name, field in ordered:
            if model_name.endswith("Draft"):
                continue
            print("model_name", model_name, " ::: field: ", field)
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
            print("expression: ", expression)
            try:
                value = evaluate_formula(target_instance, expression, model_name)
                print("model_name: ", model_name, "  :::  field: ", field, "  :::  value: ", value)
                Model = apps.get_model('user', model_name)
                
                if model_name == "IncrementDetailsSummary":
                    Model.objects.filter(id=target_instance.id).update(**{field: value})
                else:
                    Model.objects.filter(employee=target_instance.employee).update(**{field: value})
                    
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



from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps
from .models import (
    CurrentPackageDetailsDraft, ProposedPackageDetailsDraft, FinancialImpactPerMonthDraft,
    IncrementDetailsSummary, ProposedPackageDetails, FinancialImpactPerMonth, FieldFormula
)
from .utils import topological_sort, evaluate_formula, update_draft_department_team_increment_summary

@receiver(post_save, sender=CurrentPackageDetailsDraft)
@receiver(post_save, sender=ProposedPackageDetailsDraft)
@receiver(post_save, sender=FinancialImpactPerMonthDraft)
def update_draft_increment_summary(sender, instance, created, **kwargs):
    """
    Signal to update increment summary when a draft model is saved.
    """
    try:

        increment_details_summary = IncrementDetailsSummaryDraft.objects.filter(company = instance.employee_draft.company, department_team = instance.employee_draft.department_team)

        if not increment_details_summary.exists():
            existing_summary_status = SummaryStatus.objects.filter(summary_submitted=False)
            if not existing_summary_status.exists():
                new_summary_status = SummaryStatus.objects.create()
                IncrementDetailsSummaryDraft.objects.create(company = instance.employee_draft.company, department_team = instance.employee_draft.department_team, summaries_status = new_summary_status)
                print("new_summary_status: ", new_summary_status)
            else:
                IncrementDetailsSummaryDraft.objects.create(company = instance.employee_draft.company, department_team = instance.employee_draft.department_team, summaries_status = existing_summary_status.first())
                print("existing_summary_status: ", existing_summary_status)

        update_draft_department_team_increment_summary(sender, instance, instance.employee_draft.company, instance.employee_draft.department_team)

        # Determine context
        employee_draft = getattr(instance, 'employee_draft', None)
        employee = employee_draft.employee if employee_draft else getattr(instance, 'employee', None)    

        print("employee_draft.id: ", employee_draft.id)

        currentpackagedetailsdraft_dr = getattr(employee_draft, 'currentpackagedetailsdraft', None)
        if not currentpackagedetailsdraft_dr:
            currentpackagedetails = employee.currentpackagedetails
            CurrentPackageDetailsDraft.objects.get_or_create(employee_draft=employee_draft, 
                                                    gross_salary=currentpackagedetails.gross_salary, 
                                                    vehicle=currentpackagedetails.vehicle, 
                                                    fuel_limit=currentpackagedetails.fuel_limit, 
                                                    mobile_provided=currentpackagedetails.mobile_provided, 
                                                    fuel_litre=currentpackagedetails.fuel_litre, 
                                                    vehicle_allowance=currentpackagedetails.vehicle_allowance, 
                                                    total=currentpackagedetails.total, 
                                                    company_pickup=currentpackagedetails.company_pickup, 
                                                    is_deleted=currentpackagedetails.is_deleted
                                                )
            
        
        proposedpackagedetailsdraft_dr = getattr(employee_draft, 'proposedpackagedetailsdraft', None)
        if not proposedpackagedetailsdraft_dr:
            proposedpackagedetails = employee.proposedpackagedetails
            ProposedPackageDetailsDraft.objects.get_or_create(employee_draft=employee_draft)
            # ProposedPackageDetailsDraft.objects.create(employee_draft=employee_draft, increment_percentage=proposedpackagedetails.increment_percentage, 
            #     increased_amount=proposedpackagedetails.increased_amount, 
            #     revised_salary=proposedpackagedetails.revised_salary, 
            #     increased_fuel_amount=proposedpackagedetails.increased_fuel_amount, 
            #     revised_fuel_allowance=proposedpackagedetails.revised_fuel_allowance, 
            #     vehicle=proposedpackagedetails.vehicle, 
            #     mobile_provided=proposedpackagedetails.mobile_provided, 
            #     fuel_litre=proposedpackagedetails.fuel_litre, 
            #     vehicle_allowance=proposedpackagedetails.vehicle_allowance, 
            #     total=proposedpackagedetails.total,
            #     company_pickup=proposedpackagedetails.company_pickup, 
            #     is_deleted=proposedpackagedetails.is_deleted
            # )
            
        financialimpactpermonthdraft_dr = getattr(employee_draft, 'financialimpactpermonthdraft', None)
        if not financialimpactpermonthdraft_dr:
            financialimpactpermonth = employee.financialimpactpermonth
            FinancialImpactPerMonthDraft.objects.get_or_create(employee_draft=employee_draft)    

        company = getattr(instance, 'company', None) or (employee.company if employee else None)
        department_team = getattr(instance, 'department_team', None) or (employee.department_team if employee else None)

        # Create IncrementDetailsSummary if it doesn't exist
        # increment_details_summary = IncrementDetailsSummary.objects.filter(
        #     company=company, department_team=department_team
        # )
        # if not increment_details_summary.exists():
        #     IncrementDetailsSummary.objects.create(
        #         company=company, department_team=department_team
        #     )

        # Map sender to corresponding non-draft model for reference
        model_mapping = {
            'CurrentPackageDetailsDraft': 'CurrentPackageDetails',
            'ProposedPackageDetailsDraft': 'ProposedPackageDetails',
            'FinancialImpactPerMonthDraft': 'FinancialImpactPerMonth',
            'IncrementDetailsSummaryDraft': 'IncrementDetailsSummary'
        }
        sender_name = sender._meta.model_name
        is_draft = sender_name.endswith('draft')

        # Get all formulas for the company
        formulas = FieldFormula.objects.filter(company=company).select_related('formula')

        # Prioritize employee-specific formulas
        employee_formulas = formulas.filter(employee=employee, department_team=department_team) if employee else formulas.none()
        department_formulas = formulas.filter(employee__isnull=True, department_team=department_team)
        formula_ids = list(employee_formulas.values_list('id', flat=True))
        formula_ids += list(department_formulas.exclude(id__in=employee_formulas).values_list('id', flat=True))
        formulas = FieldFormula.objects.filter(id__in=formula_ids).select_related('formula')

        if not formulas:
            print(f"No formulas found for company={company}, department_team={department_team}, employee={employee}")
            return

        # Perform topological sort with context
        print(formulas)
        ordered = topological_sort(formulas, company=company, employee=employee, department_team=department_team)
        print("ordered: ", ordered)

        for model_name, field in ordered:
            # Map model to draft version if sender is a draft model
            target_model_name = model_name + 'Draft' if is_draft and model_name in model_mapping.values() else model_name
            if not target_model_name.endswith('Draft') and is_draft:
                continue  # Skip non-draft models when processing drafts

            # Prefer employee-specific formula, else department-specific
            field_formula = employee_formulas.filter(target_model=model_name, target_field=field).first() or \
                           department_formulas.filter(target_model=model_name, target_field=field).first()
            if not field_formula:
                print(f"No formula found for {model_name}.{field}")
                continue

            # Choose instance
            if target_model_name == "IncrementDetailsSummary" or target_model_name == "IncrementDetailsSummaryDraft":
                target_instance = IncrementDetailsSummary.objects.filter(
                    company=company, department_team=department_team
                ).first() if target_model_name == "IncrementDetailsSummary" else \
                IncrementDetailsSummaryDraft.objects.filter(
                    company=company, department_team=department_team
                ).first()
            else:
                target_instance = instance
                target_instance.refresh_from_db()

            if not target_instance:
                print(f"No instance found for {target_model_name} with company={company}, department_team={department_team}")
                continue

            expression = field_formula.formula.formula_expression
            try:
                print("eveavavavav isdraff: ", is_draft, "  ::: target_model_name: ", target_model_name)
                value = evaluate_formula(
                    target_instance, expression, target_model_name, is_draft=is_draft, employee_draft=employee_draft
                )
                print(f"model_name: {target_model_name}, field: {field}, value: {value}")
                Model = apps.get_model('user', target_model_name)
                # Model.objects.filter(id=target_instance.id).update(**{field: value})

                if Model._meta.model_name == "incrementdetailssummarydraft":
                    Model.objects.filter(id=target_instance.id).update(**{field: value})
                else:
                    Model.objects.filter(employee_draft=target_instance.employee_draft).update(**{field: value})
                instance.refresh_from_db()
            except ValueError as e:
                print(f"Error evaluating formula for {target_model_name}.{field}: {e}")

    except Exception as e:
        print(f"Error in updating increment summary: {e}")

# @receiver(post_save, sender=CurrentPackageDetailsDraft)
# @receiver(post_save, sender=ProposedPackageDetailsDraft)
# @receiver(post_save, sender=FinancialImpactPerMonthDraft)
# def update_draft_increment_summary(sender, instance, created, **kwargs):
#     """
#     Signal to check the driver wallet amount when a DriverAdditional is saved.
#     """
#     try:
#         # Determine context
#         employee_draft = getattr(instance, 'employee_draft', None)
#         employee = employee_draft.employee
#         company = getattr(instance, 'company', None) or (employee.company if employee else None)
#         department_team = getattr(instance, 'department_team', None) or (employee.department_team if employee else None)

#         # Get all formulas for the company
#         # formulas = FieldFormula.objects.filter(company=company).select_related('formula')
#         formulas = FieldFormula.objects.filter(target_model__endswith='Draft').select_related('formula')

#         # Prioritize employee-specific formulas
#         employee_formulas = formulas.filter(employee=employee, department_team=department_team) if employee else formulas.none()
#         print("employee_formulas: ", employee_formulas)
#         department_formulas = formulas.filter(employee__isnull=True, department_team=department_team)
#         print("department_formulas: ", department_formulas)
#         # Combine, prioritizing employee formulas
#         formula_ids = list(employee_formulas.values_list('id', flat=True))
#         formula_ids += list(department_formulas.exclude(id__in=employee_formulas).values_list('id', flat=True))
#         print("formula_ids: ", formula_ids)
#         formulas = FieldFormula.objects.filter(id__in=formula_ids).select_related('formula')

#         if not formulas:
#             print(f"No formulas found for company={company}, department_team={department_team}, employee={employee}")
#             return

#         # Topological sort with context
#         ordered = topological_sort(formulas, company=company, employee=employee, department_team=department_team)
#         print("ordered: ", ordered)

#         for model_name, field in ordered:
#             if not model_name.endswith("Draft"):
#                 continue
#             print("model_name, field: ", model_name, field)
#             # Prefer employee-specific formula, else department-specific
#             model_name_original_table = model_name.removesuffix('Draft')
#             field_formula = employee_formulas.filter(target_model=model_name_original_table, target_field=field).first() or \
#                            department_formulas.filter(target_model=model_name_original_table, target_field=field).first()
#             if not field_formula:
#                 print(f"No formula found for {model_name}.{field}")
#                 continue

#             # Choose instance
#             if model_name == "IncrementDetailsSummaryDraft":
#                 target_instance = IncrementDetailsSummaryDraft.objects.filter(
#                     company=company,
#                     department_team=department_team
#                 ).first()
#             else:
#                 instance.refresh_from_db()
#                 target_instance = instance

#             if not target_instance:
#                 print(f"No instance found for {model_name} with company={company}, department_team={department_team}")
#                 continue

#             expression = field_formula.formula.formula_expression
#             try:
#                 value = evaluate_formula(target_instance, expression, model_name, draft_table=True)
#                 print("model_name: ", model_name, "  :::  field: ", field, "  :::  value: ", value)
#                 Model = apps.get_model('user', model_name)
#                 Model.objects.filter(id=target_instance.id).update(**{field: value})
#             except ValueError as e:
#                 print(f"Error evaluating formula for {model_name}.{field}: {e}")

#     except Exception as e:
#         print(f"Error in updating increment summary: {e}")
#         # logger.error(f"Error in checking driver wallet balance: {e}", extra={'id': instance.id})


@receiver(post_save,sender=DepartmentTeams)
def add_new_increment_details_summary_record(sender, instance, created, **kwargs):
    """
    Signal to create incremental detail summary entry for the newly created department team.
    Also checks if a new summary status entry has to be created or not. 
    """
    try:
        if created:
            existing_summary_status = SummaryStatus.objects.filter(summary_submitted=False)
            if not existing_summary_status.exists():
                new_summary_status = SummaryStatus.objects.create()
                IncrementDetailsSummary.objects.create(company = instance.company, department_team = instance, summaries_status = new_summary_status)
                print("new_summary_status: ", new_summary_status)
            else:
                IncrementDetailsSummary.objects.create(company = instance.company, department_team = instance, summaries_status = existing_summary_status.first())
                print("existing_summary_status: ", existing_summary_status)

    except Exception as e:
        print(f"Error in adding new increment details summary record: {e}")
        # logger.error(f"Error in checking driver wallet balance: {e}", extra={'id': instance.id})