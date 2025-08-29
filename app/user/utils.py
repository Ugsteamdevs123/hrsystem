from .models import CurrentPackageDetails, ProposedPackageDetails, FinancialImpactPerMonth, IncrementDetailsSummary, configurations, Employee, hr_assigned_companies, DepartmentTeams
from django.db.models import Sum, Prefetch, Avg
from decimal import Decimal


def update_department_team_increment_summary(sender, instance, company, department_team):
    try:
        employee_count = Employee.objects.filter(company=company, department_team=department_team).count()
        if sender is CurrentPackageDetails:
            current_package = CurrentPackageDetails.objects.filter(employee__company=company, employee__department_team=department_team)
            if current_package.exists():
                print("CurrentPackageDetails")

                IncrementDetailsSummary.objects.filter(company=company, department_team=department_team).update(total_employees = employee_count)
                print("CurrentPackageDetails")
                
        if sender is ProposedPackageDetails:
            print("ProposedPackageDetails")

            proposed_package = ProposedPackageDetails.objects.filter(employee__company=company, employee__department_team=department_team)
            if proposed_package.exists():

                IncrementDetailsSummary.objects.filter(company=company, 
                                                    department_team=department_team
                                                    ).update(total_employees = employee_count,)
                print("ProposedPackageDetails")

        if sender is FinancialImpactPerMonth:
            proposed_package = ProposedPackageDetails.objects.get(employee=instance.employee)
            configuration = configurations.objects.first()
            if proposed_package:
                years = configuration.as_of_date.year - instance.employee.date_of_joining.year
                if (configuration.as_of_date.month, configuration.as_of_date.day) < (instance.employee.date_of_joining.month, instance.employee.date_of_joining.day):
                    years -= 1

                FinancialImpactPerMonth.objects.filter(id=instance.id).update(
                    serving_years = years
                )
           
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
                    queryset=DepartmentTeams.objects.all(),
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


















from django.apps import apps

# ✅ Put your app labels here
ALLOWED_APPS = ["user"]  # e.g. ["hr"]

def iter_allowed_models():
    for app_label in ALLOWED_APPS:
        for m in apps.get_app_config(app_label).get_models():
            yield app_label, m

def get_model_by_name(model_name: str):
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

from collections import defaultdict, deque

def build_dependency_graph(formulas, company=None, employee=None, department_team=None):
    graph = defaultdict(list)
    indegree = defaultdict(int)
    formula_targets = set()

    for formula in formulas:
        target = (formula.target_model.strip(), formula.target_field.strip().lower())
        if company and formula.company != company:
            continue
        if employee and formula.employee and formula.employee != employee:
            continue
        if department_team and formula.department_team and formula.department_team != department_team:
            continue
        formula_targets.add(target)
        expression = formula.formula.formula_expression

        if target not in indegree:
            indegree[target] = 0

        deps = get_variables_from_expression(expression)
        for _, model, field in deps:
            dep_node = (model.strip(), field.strip().lower().replace(" ", "_"))
            if dep_node not in indegree:
                indegree[dep_node] = 0
            graph[dep_node].append(target)
            indegree[target] += 1

    return graph, indegree, formula_targets

def topological_sort(formulas, company=None, employee=None, department_team=None):
    graph, indegree, formula_targets = build_dependency_graph(formulas, company, employee, department_team)
    queue = deque([node for node, deg in indegree.items() if deg == 0])
    order = []

    while queue:
        node = queue.popleft()
        if node in formula_targets:
            order.append(node)
        for neighbor in graph[node]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)

    if len(order) != len(formula_targets):
        raise ValueError("Cycle detected or unresolved dependencies in formulas!")

    return order


# In app/utils.py
import re
from decimal import Decimal
from .models import FieldReference, FieldFormula

def get_variables_from_expression(expression):
    """Extract field references with optional aggregates like SUM[Model: Field]."""
    pattern = r'(SUM|AVG|COUNT)?\[([^:]+): ([^\]]+)\]'
    matches = re.findall(pattern, expression)
    print(f"Expression: {expression}")
    print(f"Matches: {matches}")
    result = [(match[0] or None, match[1], match[2]) for match in matches]
    if not matches:
        raise ValueError(f"No valid field references found in expression: {expression}")
    return result

def get_field_path(model_name, display_name):
    """Map display name to Django path."""
    try:
        ref = FieldReference.objects.get(model_name=model_name, display_name=display_name)
        return ref.path
    except FieldReference.DoesNotExist:
        raise ValueError(f"Field {model_name}: {display_name} not found")

def get_nested_attr(instance, path, aggregate_type=None):
    """Fetch value via Django-style path, applying aggregate if specified."""
    parts = path.split('__')
    print("parts: ", parts)
    if len(parts) > 1:  # External model field
        model_name = parts[-2].capitalize()
        field_name = parts[-1]
        print("aggregate_type: ", aggregate_type, "    ", "model_name: ", model_name , "   ", "field_name: ", field_name , "   ")
        Model = apps.get_model('user', model_name)
        # related_field = 'employee' if 'employee' in path else parts[0]
        related_field = parts[1]
        print("instance._meta.object_name: ", instance._meta.object_name)

        if instance._meta.object_name == "IncrementDetailsSummary" and model_name=="IncrementDetailsSummary":
            filter_kwargs = {"company": instance.company, "department_team": instance.department_team}
        elif instance._meta.object_name != "IncrementDetailsSummary" and model_name=="IncrementDetailsSummary":
            filter_kwargs = {"company": instance.employee.company, "department_team": instance.employee.department_team}
        elif instance._meta.object_name == "IncrementDetailsSummary" and model_name!="IncrementDetailsSummary":
            filter_kwargs = {"employee__company": instance.company, "employee__department_team": instance.department_team}
        else:
            filter_kwargs = {"employee__company": instance.employee.company, "employee__department_team": instance.employee.department_team}

        if aggregate_type:
            if aggregate_type == 'SUM':
                result = Model.objects.filter(**filter_kwargs).aggregate(Sum(field_name)) or {f"{field_name}__sum": 0}
                print("resulttt: ", result)
                return result[f"{field_name}__sum"] or 0
            elif aggregate_type == 'AVG':
                result = Model.objects.filter(**filter_kwargs).aggregate(Avg(field_name)) or {f"{field_name}__avg": 0}
                print("resulttt: ", result)
                return result[f"{field_name}__avg"] or 0
            elif aggregate_type == 'COUNT':
                return Model.objects.filter(**filter_kwargs).count()
        else:
            obj = instance
            for part in parts:
                if obj._meta.object_name == 'IncrementDetailsSummary' and part in ['employee', 'incrementdetailssummary']:
                    # 'continue' because IncrementDetailsSummary do not have foreign field 'employee', hence ther will be no reverse lookup 'incrementdetailssummary'
                    continue
                obj = getattr(obj, part)
            return obj
    else:
        return getattr(instance, path)
    

def sanitize_expression(expression, context):
    mapping = {}
    for i, key in enumerate(context.keys(), 1):
        var_name = f"var{i}"  # safe Python identifier
        mapping[key] = var_name
        expression = expression.replace(key, var_name)
    new_context = {v: context[k] for k, v in mapping.items()}
    print("new_context: ", new_context)
    return expression, new_context


def evaluate_formula(instance, expression, target_model):
    """Evaluate formula, replacing [Model: Field] or SUM[Model: Field] with values."""
    context = {}
    for aggregate_type, model_name, display_name in get_variables_from_expression(expression):
        print("aggregate_type, model_name, display_name: ", aggregate_type, model_name, display_name)
        path = get_field_path(model_name, display_name)
        print("path: ", path)
        value = get_nested_attr(
            instance,
            path,
            aggregate_type if model_name != target_model else None
        )
        print("value: ", value)
        if isinstance(value, Decimal):
            value = float(value)
        context[f'{aggregate_type or ""}[{model_name}: {display_name}]'] = value

    try:
        print("expression: ", expression)
        print("context: ", context)
        expr = expression.split('=', 1)[1].strip() if '=' in expression else expression
        print("expr: ", expr)
        expr, safe_context = sanitize_expression(expr, context)
        result = eval(expr, {"__builtins__": {}}, safe_context)
        print("result: ", result)
        return Decimal(result)
    except Exception as e:
        print("error in evaluating formula: ", e)
        raise ValueError(f"Formula evaluation failed: {e}")
# def get_nested_attr(instance, path):
#     parts = path.split('__')
#     obj = instance
#     for part in parts:
#         obj = getattr(obj, part)
#         print("obj: ", obj)
#     return obj
