from datetime import datetime
from decimal import Decimal
from collections import defaultdict, deque
import re

from .models import (
    CurrentPackageDetails, 
    ProposedPackageDetails, 
    FinancialImpactPerMonth, 
    IncrementDetailsSummary, 
    Configurations, 
    Employee, 
    hr_assigned_companies, 
    DepartmentTeams,
    EmployeeDraft, 
    CurrentPackageDetailsDraft, 
    ProposedPackageDetailsDraft, 
    FinancialImpactPerMonthDraft, 
    IncrementDetailsSummaryDraft,
    FieldReference
)

from django.apps import apps
from django.db.models import Prefetch


def normalize_field_name(name):
    # Lowercase, remove extra spaces, replace spaces with underscores
    print(name)
    print(type(name))
    name = name.strip()
    refined_name = re.sub(r'\s+', ' ', name)       # Collapse multiple spaces
    name = refined_name.lower().replace(' ', '_')  # Replace space with underscore
    return refined_name, name


def update_draft_department_team_increment_summary(sender, instance, company, department_team):
    try:
        employee_count = Employee.objects.filter(company=company, department_team=department_team).count()
        employee_draft = EmployeeDraft.objects.filter(company=company, department_team=department_team)
        if not employee_draft.exists():
            return
        if sender is CurrentPackageDetailsDraft:
            current_package = CurrentPackageDetailsDraft.objects.filter(employee_draft__company=company, employee_draft__department_team=department_team)
            if current_package.exists():
                IncrementDetailsSummaryDraft.objects.filter(company=company, department_team=department_team).update(total_employees = employee_count)
                
        if sender is ProposedPackageDetailsDraft:
            proposed_package = ProposedPackageDetailsDraft.objects.filter(employee_draft__company=company, employee_draft__department_team=department_team)
            if proposed_package.exists():

                IncrementDetailsSummaryDraft.objects.filter(company=company, department_team=department_team).update(total_employees = employee_count,)

        if sender is FinancialImpactPerMonthDraft:
            configuration = Configurations.objects.first()
            if configuration:
                years = configuration.as_of_date.year - instance.employee_draft.employee.date_of_joining.year
                if (configuration.as_of_date.month, configuration.as_of_date.day) < (instance.employee_draft.employee.date_of_joining.month, instance.employee_draft.employee.date_of_joining.day):
                    years -= 1
                    if years < 0:
                        years = 0

                FinancialImpactPerMonthDraft.objects.filter(id=instance.id).update(serving_years = years)
           
    except Exception as e:
        print(f"Error in updating draft department team increment summary: {e}")


def update_department_team_increment_summary(sender, instance, company, department_team):
    try:
        employee_count = Employee.objects.filter(company=company, department_team=department_team).count()
        
        if sender in [Employee, CurrentPackageDetails, ProposedPackageDetails]:
                IncrementDetailsSummary.objects.filter(company=company, department_team=department_team).update(total_employees = employee_count,)

        if sender is FinancialImpactPerMonth:
            proposed_package = ProposedPackageDetails.objects.get(employee=instance.employee)
            configuration = Configurations.objects.first()
            if proposed_package:

                # Ensure both are datetime/date
                as_of_date = configuration.as_of_date
                date_of_joining = instance.employee.date_of_joining

                # Convert string to date if needed
                if isinstance(as_of_date, str):
                    as_of_date = datetime.strptime(as_of_date, "%Y-%m-%d").date()

                if isinstance(date_of_joining, str):
                    date_of_joining = datetime.strptime(date_of_joining, "%Y-%m-%d").date()

                years = as_of_date.year - date_of_joining.year
                if (as_of_date.month, as_of_date.day) < (date_of_joining.month, date_of_joining.day):
                    years -= 1

                FinancialImpactPerMonth.objects.filter(id=instance.id).update(serving_years = years)
           
    except Exception as e:
        print(f"Error in updating department team increment summary: {e}")


def get_companies_and_department_teams(hr_id):
    try:
        assigned_companies = (
            hr_assigned_companies.objects
            .filter(hr=hr_id)
            .select_related("company")
            .prefetch_related(
                Prefetch(
                    "company__departmentteams_set",  # reverse relation from Company → DepartmentTeams
                    queryset=DepartmentTeams.objects.filter(is_deleted=False),
                    to_attr="prefetched_departments"
                )
            )
        )

        return [
            {
                "company_id": ac.company.id,
                "company_name": ac.company.name,
                "departments": [
                    {"id": dept.id, "name": dept.name}
                    for dept in getattr(ac.company, "prefetched_departments", [])
                ]
            }
            for ac in assigned_companies
        ]
    except Exception as e:
        print(f"Error in fetching hr assigned companies and their respective deparment teams: {e}")


# ✅ Put your app labels here
ALLOWED_APPS = ["user"]  # e.g. ["hr"]

def iter_allowed_models():
    for app_label in ALLOWED_APPS:
        for m in apps.get_app_config(app_label).get_models():
            yield app_label, m

def get_model_by_name(model_name: str):
    print("model_name: ", model_name)
    for app_label, m in iter_allowed_models():
        if m.__name__ == model_name:
            return app_label, m
    return None, None

def list_fields(model):
    if not model:
        return []
    # include only concrete, non auto-created, non-M2M fields
    return [
        f.name for f in model._meta.get_fields()
        if getattr(f, "concrete", False)
        and not getattr(f, "auto_created", False)
        and not getattr(f, "many_to_many", False)
    ]

# def build_dependency_graph(formulas, company=None, employee=None, department_team=None):
#     graph = defaultdict(list)
#     indegree = defaultdict(int)
#     formula_targets = set()

#     for formula in formulas:
#         target = (formula.target_model.strip(), formula.target_field.strip().lower())
#         if company and formula.company != company:
#             continue
#         if employee and formula.employee and formula.employee != employee:
#             continue
#         if department_team and formula.department_team and formula.department_team != department_team:
#             continue
#         formula_targets.add(target)
#         expression = formula.formula.formula_expression

#         if target not in indegree:
#             indegree[target] = 0

#         deps = get_variables_from_expression(expression)
#         for _, model, field in deps:
#             dep_node = (model.strip(), field.strip().lower().replace(" ", "_"))
#             if dep_node not in indegree:
#                 indegree[dep_node] = 0
#             graph[dep_node].append(target)
#             indegree[target] += 1

#     return graph, indegree, formula_targets

# def topological_sort(formulas, company=None, employee=None, department_team=None):
#     graph, indegree, formula_targets = build_dependency_graph(formulas, company, employee, department_team)
#     queue = deque([node for node, deg in indegree.items() if deg == 0])
#     order = []

#     while queue:
#         node = queue.popleft()
#         if node in formula_targets:
#             order.append(node)
#         for neighbor in graph[node]:
#             indegree[neighbor] -= 1
#             if indegree[neighbor] == 0:
#                 queue.append(neighbor)

#     if len(order) != len(formula_targets):
#         raise ValueError("Cycle detected or unresolved dependencies in formulas!")

#     return order


# # In app/utils.py
# import re
# from decimal import Decimal
# from .models import FieldReference, FieldFormula

# def get_variables_from_expression(expression):
#     """Extract field references with optional aggregates like SUM[Model: Field]."""
#     pattern = r'(SUM|AVG|COUNT)?\[([^:]+): ([^\]]+)\]'
#     matches = re.findall(pattern, expression)
#     print(f"Expression: {expression}")
#     print(f"Matches: {matches}")
#     result = [(match[0] or None, match[1], match[2]) for match in matches]
#     if not matches:
#         raise ValueError(f"No valid field references found in expression: {expression}")
#     return result

# def get_field_path(model_name, display_name):
#     """Map display name to Django path."""
#     try:
#         ref = FieldReference.objects.get(model_name=model_name, display_name=display_name)
#         return ref.path
#     except FieldReference.DoesNotExist:
#         raise ValueError(f"Field {model_name}: {display_name} not found")

# def get_nested_attr(instance, path, aggregate_type=None):
#     """Fetch value via Django-style path, applying aggregate if specified."""
#     parts = path.split('__')
#     print("parts: ", parts)
#     if len(parts) > 1:  # External model field
#         model_name = parts[-2].capitalize()
#         field_name = parts[-1]
#         print("aggregate_type: ", aggregate_type, "    ", "model_name: ", model_name , "   ", "field_name: ", field_name , "   ")
#         Model = apps.get_model('user', model_name)
#         # related_field = 'employee' if 'employee' in path else parts[0]
#         related_field = parts[1]
#         print("instance._meta.object_name: ", instance._meta.object_name)

#         if instance._meta.object_name == "IncrementDetailsSummary" and model_name=="IncrementDetailsSummary":
#             filter_kwargs = {"company": instance.company, "department_team": instance.department_team}
#         elif instance._meta.object_name != "IncrementDetailsSummary" and model_name=="IncrementDetailsSummary":
#             filter_kwargs = {"company": instance.employee.company, "department_team": instance.employee.department_team}
#         elif instance._meta.object_name == "IncrementDetailsSummary" and model_name!="IncrementDetailsSummary":
#             filter_kwargs = {"employee__company": instance.company, "employee__department_team": instance.department_team}
#         else:
#             filter_kwargs = {"employee__company": instance.employee.company, "employee__department_team": instance.employee.department_team}

#         if aggregate_type:
#             if aggregate_type == 'SUM':
#                 result = Model.objects.filter(**filter_kwargs).aggregate(Sum(field_name)) or {f"{field_name}__sum": 0}
#                 print("resulttt: ", result)
#                 return result[f"{field_name}__sum"] or 0
#             elif aggregate_type == 'AVG':
#                 result = Model.objects.filter(**filter_kwargs).aggregate(Avg(field_name)) or {f"{field_name}__avg": 0}
#                 print("resulttt: ", result)
#                 return result[f"{field_name}__avg"] or 0
#             elif aggregate_type == 'COUNT':
#                 return Model.objects.filter(**filter_kwargs).count()
#         else:
#             obj = instance
#             for part in parts:
#                 if obj._meta.object_name == 'IncrementDetailsSummary' and part in ['employee', 'incrementdetailssummary']:
#                     # 'continue' because IncrementDetailsSummary do not have foreign field 'employee', hence ther will be no reverse lookup 'incrementdetailssummary'
#                     continue
#                 obj = getattr(obj, part)
#             return obj
#     else:
#         return getattr(instance, path)
    

# def sanitize_expression(expression, context):
#     mapping = {}
#     for i, key in enumerate(context.keys(), 1):
#         var_name = f"var{i}"  # safe Python identifier
#         mapping[key] = var_name
#         expression = expression.replace(key, var_name)
#     new_context = {v: context[k] for k, v in mapping.items()}
#     print("new_context: ", new_context)
#     return expression, new_context


# def evaluate_formula(instance, expression, target_model):
#     """Evaluate formula, replacing [Model: Field] or SUM[Model: Field] with values."""
#     context = {}
#     for aggregate_type, model_name, display_name in get_variables_from_expression(expression):
#         print("aggregate_type, model_name, display_name: ", aggregate_type, model_name, display_name)
#         path = get_field_path(model_name, display_name)
#         print("path: ", path)
#         value = get_nested_attr(
#             instance,
#             path,
#             aggregate_type if model_name != target_model else None
#         )
#         print("value: ", value)
#         if isinstance(value, Decimal):
#             value = float(value)
#         context[f'{aggregate_type or ""}[{model_name}: {display_name}]'] = value

#     try:
#         print("expression: ", expression)
#         print("context: ", context)
#         expr = expression.split('=', 1)[1].strip() if '=' in expression else expression
#         print("expr: ", expr)
#         expr, safe_context = sanitize_expression(expr, context)
#         result = eval(expr, {"__builtins__": {}}, safe_context)
#         print("result: ", result)
#         return Decimal(result)
#     except Exception as e:
#         print("error in evaluating formula: ", e)
#         raise ValueError(f"Formula evaluation failed: {e}")
# # def get_nested_attr(instance, path):
# #     parts = path.split('__')
# #     obj = instance
# #     for part in parts:
# #         obj = getattr(obj, part)
# #         print("obj: ", obj)
# #     return obj

def get_variables_from_expression(expression):
    """Extract field references with optional aggregates like SUM[Model: Field]."""
    pattern = r'(SUM|AVG|COUNT)?\[([^:]+): ([^\]]+)\]'
    matches = re.findall(pattern, expression)
    # print(f"Expression: {expression}, Matches: {matches}")
    if not matches:
        raise ValueError(f"No valid field references found in expression: {expression}")
    return [(match[0] or None, match[1], match[2]) for match in matches]

def get_field_path(model_name, display_name):
    """Map display name to Django path, supporting draft models."""
    try:
        ref = FieldReference.objects.get(model_name=model_name, display_name=display_name)
        return ref.path
    except FieldReference.DoesNotExist:
        # Try with draft model
        if not model_name.endswith('Draft'):
            try:
                ref = FieldReference.objects.get(model_name=f"{model_name}Draft", display_name=display_name)
                return ref.path
            except FieldReference.DoesNotExist:
                raise ValueError(f"Field {model_name} or {model_name}Draft: {display_name} not found")
        raise ValueError(f"Field {model_name}: {display_name} not found")

def get_nested_attr(instance, path, aggregate_type=None, is_draft=False, employee_draft=None):
    """Fetch value via Django-style path, applying aggregate if specified, prioritizing draft tables."""
    # print("PATH: is draft?", path, is_draft)
    # print("path: ", path)
    if 'employee__employee' in path:
        path = path.replace('employee__employee', 'employee')
    # print("PATH: is draft?", path, is_draft)
    path = path.replace('employee', 'employee_draft') if is_draft else path
    parts = path.split('__')
    if parts[-2] == "employee_draft":
        parts[-2] = "employeedraft"
    elif parts[-2] not in ['configurations', 'dynamic_attribute']:
        parts[-2] = parts[-2]+'draft' if is_draft else parts[-2]
    elif parts[-2] == 'dynamic_attribute' and instance._meta.object_name in ['EmployeeDraft', 'Employee']:
        parts.pop(0)
    print("parts: ", parts)
    # print("instance: ", instance._meta.object_name)
    model_mapping = {
        'employee': 'Employee',
        'currentpackagedetails': 'CurrentPackageDetails',
        'proposedpackagedetails': 'ProposedPackageDetails',
        'financialimpactpermonth': 'FinancialImpactPerMonth',
        'incrementdetailssummary': 'IncrementDetailsSummary'
    }

    model_mapping_draft = {
        'employeedraft': 'EmployeeDraft',
        'currentpackagedetailsdraft': 'CurrentPackageDetailsDraft',
        'proposedpackagedetailsdraft': 'ProposedPackageDetailsDraft',
        'financialimpactpermonthdraft': 'FinancialImpactPerMonthDraft',
        'incrementdetailssummarydraft': 'IncrementDetailsSummaryDraft'
    }

    if len(parts) > 1:  # External model field
        if len(parts) == 2:
            model_name = parts[-2].replace('_', '')
        else:
            model_name = parts[-2]
        field_name = parts[-1]
        # print("model name: ", model_name)
        target_model_name = model_mapping_draft.get(model_name, model_name) if is_draft else model_mapping.get(model_name, model_name)
        Model = apps.get_model('user', target_model_name)

        # Build filter kwargs based on context
        # if target_model_name == "IncrementDetailsSummary" or target_model_name == "IncrementDetailsSummaryDraft":
        #     filter_kwargs = {"company": instance.company, "department_team": instance.department_team}
        # elif is_draft and target_model_name.endswith('Draft'):
        #     filter_kwargs = {
        #         "employee_draft__employee__company": instance.employee_draft.employee.company 
        #         if hasattr(instance, 'employee_draft') else instance.employee.company,
        #         "employee_draft": employee_draft
        #     }
        # else:
        #     filter_kwargs = {"employee__company": instance.employee_draft.employee.company 
        #                     if hasattr(instance, 'employee_draft') else instance.employee.company,
        #                     "employee__department_team": instance.employee_draft.employee.department_team 
        #                     if hasattr(instance, 'employee_draft') else instance.employee.department_team}


        # print("abcdefg is_draft: ", is_draft, " ::: target_model_name: ", target_model_name, " ::: model_name: ", model_name)
        # Get filter kwargs for non_draft tables at all case as they will be used to fetch those records for increment details summary draft where some employee
        # records are not draft and their values need to be fetched from original tables.
        print("model_name: ", model_name, "instance._meta.object_name: ", instance._meta.object_name)
        if is_draft and target_model_name.endswith('Draft'):
            if instance._meta.object_name == "IncrementDetailsSummaryDraft" and (target_model_name=="IncrementDetailsSummaryDraft" or target_model_name=='EmployeeDraft'):
                filter_kwargs = {"company": instance.company, "department_team": instance.department_team}
                filter_kwargs_non_draft = {"company": instance.company, "department_team": instance.department_team}
            elif instance._meta.object_name != "IncrementDetailsSummaryDraft" and (target_model_name=="IncrementDetailsSummaryDraft" or target_model_name=='EmployeeDraft'):
                filter_kwargs = {"company": instance.employee_draft.employee.company, "department_team": instance.employee_draft.employee.department_team}
                filter_kwargs_non_draft = {"company": instance.employee_draft.employee.company, "department_team": instance.employee_draft.employee.department_team}
            elif instance._meta.object_name == "IncrementDetailsSummaryDraft" and target_model_name!="IncrementDetailsSummaryDraft":
                filter_kwargs = {"employee_draft__company": instance.company, "employee_draft__department_team": instance.department_team}
                filter_kwargs_non_draft = {"employee__company": instance.company, "employee__department_team": instance.department_team}
            else:
                filter_kwargs = {"employee_draft__company": instance.employee_draft.employee.company, "employee_draft__department_team": instance.employee_draft.employee.department_team}
                filter_kwargs_non_draft = {"employee__company": instance.employee_draft.employee.company, "employee__department_team": instance.employee_draft.employee.department_team}
            # print("filter_kwargs draft: ", filter_kwargs)
            # print("filter_kwargs_non_draft draft (for non draft): ", filter_kwargs_non_draft)
        else:
            if target_model_name!='configurations':
                if instance._meta.object_name == "IncrementDetailsSummary" and (model_name=="IncrementDetailsSummary" or target_model_name=="Employee"):
                    filter_kwargs = {"company": instance.company, "department_team": instance.department_team}
                elif instance._meta.object_name != "IncrementDetailsSummary" and (model_name=="IncrementDetailsSummary" or target_model_name=="Employee"):
                    filter_kwargs = {"company": instance.employee.company, "department_team": instance.employee.department_team}
                elif instance._meta.object_name in ("IncrementDetailsSummary", "Employee") and model_name!="IncrementDetailsSummary":
                    filter_kwargs = {"employee__company": instance.company, "employee__department_team": instance.department_team}
                else:
                    filter_kwargs = {"employee__company": instance.employee.company, "employee__department_team": instance.employee.department_team}

                # print("filter_kwargs: ", filter_kwargs)

        if aggregate_type:
            if aggregate_type in ['SUM', 'AVG']:
                # First, get draft rows for employees with drafts
                draft_model_name = f"{model_name}Draft" if model_name in model_mapping else model_name
                # print("instance name: ", instance._meta.object_name)
                # print("aggrgate - model name", model_name)
                # print("aggrgate - draft model name", draft_model_name)
                
                draft_values = []
                non_draft_employees = []

                if is_draft:
                    draft_model_name = model_mapping_draft.get(model_name, model_name)
                    # print("aggrgate - updated draft model name", draft_model_name)
                    DraftModel = apps.get_model('user', draft_model_name) if model_name in model_mapping_draft else None
                    # print("draft model: ", DraftModel)
                    
                    if target_model_name == 'EmployeeDraft':
                        filter_kwargs["eligible_for_increment"] = True
                        filter_kwargs["resign"] = False
                        draft_rows = Model.objects.filter(**filter_kwargs).values('employee_id', field_name)
                    
                    else:
                        filter_kwargs["employee_draft__eligible_for_increment"] = True
                        filter_kwargs["employee_draft__resign"] = False
                        draft_rows = Model.objects.filter(**filter_kwargs).values('employee_draft__employee_id', field_name)
                    
                    # draft_rows = DraftModel.objects.filter(
                    #     employee_draft__employee__company=instance.employee_draft.employee.company
                    #     if hasattr(instance, 'employee_draft') else instance.employee.company,
                    #     employee_draft__employee__department_team=instance.employee_draft.employee.department_team
                    #     if hasattr(instance, 'employee_draft') else instance.employee.department_team
                    # ).values('employee_draft__employee_id', field_name)
                    draft_employee_ids = set()
                    for row in draft_rows:
                        value = row[field_name]
                        if value is not None:
                            draft_values.append(float(value))
                            if target_model_name == 'EmployeeDraft':
                                draft_employee_ids.add(row['employee_id'])
                            else:
                                draft_employee_ids.add(row['employee_draft__employee_id'])

                    # Get non-draft rows for employees without drafts (from original non-draft tables)
                    non_draft_model = apps.get_model('user', target_model_name[:-5]) # target_model_name ends with 'Draft' in this case so we slice it to remove 'Draft'
                    if Model._meta.model_name == 'employeedraft':
                        # non_draft_employees = Model.objects.filter(**filter_kwargs).exclude(employee_id__in=draft_employee_ids).values(field_name)
                        filter_kwargs_non_draft["eligible_for_increment"] = True
                        filter_kwargs_non_draft["resign"] = False
                        non_draft_employees = non_draft_model.objects.filter(**filter_kwargs_non_draft).exclude(id__in=draft_employee_ids).values(field_name)
                    else:
                        # non_draft_employees = Model.objects.filter(**filter_kwargs).exclude(employee_draft__employee_id__in=draft_employee_ids).values(field_name)
                        filter_kwargs_non_draft["employee__eligible_for_increment"] = True
                        filter_kwargs_non_draft["employee__resign"] = False
                        non_draft_employees = non_draft_model.objects.filter(**filter_kwargs_non_draft).exclude(employee_id__in=draft_employee_ids).values(field_name)
                    # non_draft_employees = Model.objects.filter(
                    #     employee__company=instance.employee_draft.employee.company
                    #     if hasattr(instance, 'employee_draft') else instance.employee.company,
                    #     employee__department_team=instance.employee_draft.employee.department_team
                    #     if hasattr(instance, 'employee_draft') else instance.employee.department_team
                    # ).exclude(employee_id__in=draft_employee_ids).values(field_name)
                    for row in non_draft_employees:
                        value = row[field_name]
                        if value is not None:
                            draft_values.append(float(value))

                else:
                    if target_model_name=="Employee":
                        filter_kwargs["eligible_for_increment"] = True
                        filter_kwargs["resign"] = False
                    else:
                        filter_kwargs["employee__eligible_for_increment"] = True
                        filter_kwargs["employee__resign"] = False
                    # No draft model or not in draft mode, use original model
                    rows = Model.objects.filter(**filter_kwargs).values(field_name)
                    for row in rows:
                        value = row[field_name]
                        if value is not None:
                            draft_values.append(float(value))

                if aggregate_type == 'SUM':
                    return sum(draft_values) if draft_values else 0
                elif aggregate_type == 'AVG':
                    return sum(draft_values) / len(draft_values) if draft_values else 0
            elif aggregate_type == 'COUNT':
                if is_draft and model_name in model_mapping:
                    DraftModel = apps.get_model('user', model_mapping[model_name])
                    draft_count = DraftModel.objects.filter(
                        employee_draft__employee__company=instance.employee_draft.employee.company
                        if hasattr(instance, 'employee_draft') else instance.employee.company,
                        employee_draft__employee__department_team=instance.employee_draft.employee.department_team
                        if hasattr(instance, 'employee_draft') else instance.employee.department_team
                    ).count()
                    non_draft_count = Model.objects.filter(
                        **filter_kwargs
                    ).exclude(
                        employee_id__in=DraftModel.objects.filter(
                            employee_draft__employee__company=instance.employee_draft.employee.company
                            if hasattr(instance, 'employee_draft') else instance.employee.company,
                            employee_draft__employee__department_team=instance.employee_draft.employee.department_team
                            if hasattr(instance, 'employee_draft') else instance.employee.department_team
                        ).values('employee_draft__employee_id')
                    ).count()
                    return draft_count + non_draft_count
                return Model.objects.filter(**filter_kwargs).count()
        else:
            # Non-aggregate field access
            # obj = instance
            # previous_part = ''
            # for part in parts:
            #     if part == 'configurations' or previous_part == 'configurations':
            #         previous_part = 'configurations'
            #         if part == 'configurations':
            #             continue
            #         ConfigurationModel = apps.get_model('user', 'Configurations').objects.first()  # or filter by relation
            #         print("1")
            #         obj = getattr(ConfigurationModel, part)
            #     else:
            #         print("2")
            #         if obj._meta.object_name in ['IncrementDetailsSummary', 'IncrementDetailsSummaryDraft'] and part in ['employee', 'employee_draft', 'incrementdetailssummary', 'incrementdetailssummarydraft']:
            #             continue
            #         # if is_draft and part == 'employee' and hasattr(obj, 'employee_draft'):
            #         #     obj = getattr(obj, 'employee_draft').employee
            #         else:
            #             print("3")
            #             obj = getattr(obj, part)
            # return obj
            obj = instance
            previous_part = ''
            i = 0

            while i < len(parts):
                part = parts[i]

                if part == 'configurations' or previous_part == 'configurations':
                    previous_part = 'configurations'
                    if part == 'configurations':
                        i += 1
                        continue
                    ConfigurationModel = apps.get_model('user', 'Configurations').objects.first()
                    obj = getattr(ConfigurationModel, part)
                    i += 1
                    continue

                # Handle dynamic_attribute + next key in parts
                if part == 'dynamic_attribute':
                    dynamic_attrs = getattr(obj, part, None)
                    key_to_find = None

                    # Check if next part exists as key
                    if i + 1 < len(parts):
                        key_to_find = parts[i + 1]
                        i += 1  # Consume the key part as well

                    if dynamic_attrs is not None:
                        attr = None
                        if key_to_find:
                            attr = dynamic_attrs.filter(definition__key=key_to_find).first()
                        if not attr:
                            attr = dynamic_attrs.last()
                        obj = (attr.value, attr.definition.data_type) if attr else None
                    else:
                        obj = None

                    i += 1
                    continue

                else:
                    # Defensive: if obj is a manager/queryset, get first instance
                    if hasattr(obj, 'all'):
                        obj = obj.first()

                    if obj is None:
                        break

                    if obj._meta.object_name in ['IncrementDetailsSummary', 'IncrementDetailsSummaryDraft'] and part in ['employee', 'employee_draft', 'incrementdetailssummary', 'incrementdetailssummarydraft']:
                        i += 1
                        continue
                    else:
                        obj = getattr(obj, part)
                        i += 1

            return obj

    else:
        return getattr(instance, path)

def sanitize_expression(expression, context):
    """Sanitize expression by replacing field references with safe variable names."""
    mapping = {}
    for i, key in enumerate(context.keys(), 1):
        var_name = f"var{i}"
        mapping[key] = var_name
        expression = expression.replace(key, var_name)
    new_context = {v: context[k] for k, v in mapping.items()}
    return expression, new_context

def evaluate_formula(instance, expression, target_model, is_draft=False, employee_draft=None):
    """Evaluate formula, replacing [Model: Field] or SUM[Model: Field] with values, considering drafts."""
    context = {}
    model_mapping = {
        'CurrentPackageDetails': 'CurrentPackageDetailsDraft',
        'ProposedPackageDetails': 'ProposedPackageDetailsDraft',
        'FinancialImpactPerMonth': 'FinancialImpactPerMonthDraft',
        'IncrementDetailsSummary': 'IncrementDetailsSummaryDraft'
    }
    # print(instance)
    for aggregate_type, model_name, display_name in get_variables_from_expression(expression):
        # target_model_name = model_mapping.get(model_name, model_name) if is_draft else model_name
        target_model_name = model_name
        path = get_field_path(target_model_name, display_name)
        # path = get_field_path(model_name, display_name)
        value = get_nested_attr(
            instance,
            path,
            aggregate_type if model_name != target_model else None,
            is_draft=is_draft,
            employee_draft=employee_draft
        )
        
        if isinstance(value, tuple):
            data_type = value[1]
            if data_type == 'number':
                value = float(value[0])
            else:
                value = value[0]
        elif isinstance(value, Decimal):
            value = float(value)
        context[f'{aggregate_type or ""}[{model_name}: {display_name}]'] = value

    try:
        expr = expression.split('=', 1)[1].strip() if '=' in expression else expression
        expr, safe_context = sanitize_expression(expr, context)
        # print(safe_context)
        result = eval(expr, {"__builtins__": {}}, safe_context)
        return Decimal(result)
    except Exception as e:
        raise ValueError(f"Formula evaluation failed: {e}")

# def build_dependency_graph(formulas, company=None, employee=None, department_team=None, is_draft=False):
#     """Build dependency graph for formulas, considering draft models."""
#     graph = defaultdict(list)
#     indegree = defaultdict(int)
#     formula_targets = set()
#     model_mapping = {
#         'CurrentPackageDetails': 'CurrentPackageDetailsDraft',
#         'ProposedPackageDetails': 'ProposedPackageDetailsDraft',
#         'FinancialImpactPerMonth': 'FinancialImpactPerMonthDraft',
#         'IncrementDetailsSummary': 'IncrementDetailsSummaryDraft'
#     }

#     for formula in formulas:
#         # target_model = model_mapping.get(formula.target_model, formula.target_model) if is_draft else formula.target_model
#         target_model = formula.target_model
#         target = (target_model.strip(), formula.target_field.strip().lower())
#         if company and formula.company != company:
#             continue
#         if employee and formula.employee and formula.employee != employee:
#             continue
#         if department_team and formula.department_team and formula.department_team != department_team:
#             continue
#         formula_targets.add(target)
#         expression = formula.formula.formula_expression

#         if target not in indegree:
#             indegree[target] = 0

#         deps = get_variables_from_expression(expression)
#         for _, model, field in deps:
#             dep_model = model_mapping.get(model, model) if is_draft else model
#             dep_node = (dep_model.strip(), field.strip().lower().replace(" ", "_"))
#             if dep_node not in indegree:
#                 indegree[dep_node] = 0
#             graph[dep_node].append(target)
#             indegree[target] += 1

#     return graph, indegree, formula_targets

# def topological_sort(formulas, company=None, employee=None, department_team=None, is_draft=False):
#     """Perform topological sort on formulas, considering draft models."""
#     graph, indegree, formula_targets = build_dependency_graph(formulas, company, employee, department_team, is_draft)
#     queue = deque([node for node, deg in indegree.items() if deg == 0])
#     order = []
    
#     while queue:
#         node = queue.popleft()
#         if node in formula_targets:
#             order.append(node)
#         for neighbor in graph[node]:
#             indegree[neighbor] -= 1
#             if indegree[neighbor] == 0:
#                 queue.append(neighbor)
                
#     if len(order) != len(formula_targets):
#         raise ValueError("Cycle detected or unresolved dependencies in formulas!")

#     return order

def build_dependency_graph(formulas, company=None, employee=None, department_team=None):
    graph = defaultdict(list)
    indegree = defaultdict(int)
    formula_targets = set()

    # i = 0
    for formula in formulas:
        # print("\n\nFormula: ", i)
        # i += 1
        
        target = (formula.formula.target_model.strip(), formula.formula.target_field.strip().lower())
        if company and formula.company != company:
            continue
        if department_team and formula.department_team and formula.department_team != department_team:
            continue
        formula_targets.add(target)
        expression = formula.formula.formula_expression

        if target not in indegree:
            indegree[target] = 0
            # print(f"indegree for target '{target}' set to 0: ", indegree)

        deps = get_variables_from_expression(expression)
        # print("deps: ", deps)
        for _, model, field in deps:
            dep_node = (model.strip(), field.strip().lower().replace(" ", "_"))
            # print("dep_node: ", dep_node)
            if dep_node not in indegree:
                indegree[dep_node] = 0
                # print(f"indegree for dep_node '{dep_node}' set to 0: ", indegree)
            graph[dep_node].append(target)
            # print("updated graph: ", graph)
            indegree[target] += 1
            # print("updated indegree: ", indegree)

    return graph, indegree, formula_targets

def topological_sort(formulas, company=None, employee=None, department_team=None):
    graph, indegree, formula_targets = build_dependency_graph(formulas, company, employee, department_team)
    
    # print("\n\n\nfinal grpah: ", graph)
    # print("\nfinal indegree: ", indegree)
    
    queue = deque([node for node, deg in indegree.items() if deg == 0])

    # print("\nformula_targets: ", formula_targets)
    # print("\nqueue: ", queue)
    full_order = []
    while queue:
        node = queue.popleft()
        full_order.append(node)

        for neighbor in graph[node]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)

    # After sorting, only return the target fields, in the order they appeared
    ordered = [node for node in full_order if node in formula_targets]
    
    if len(ordered) != len(formula_targets):
        raise ValueError("Cycle detected or unresolved dependencies in formulas!")
        
    return ordered