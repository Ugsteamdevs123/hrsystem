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
                gross_salary = current_package.aggregate(total_price=Sum('gross_salary'))['total_price'] or 0
                print("gross_salary: ", gross_salary)

                # IncrementDetailsSummary.objects.filter(company=company, 
                #                                     department_team=department_team
                #                                     ).update(current_salary=gross_salary,
                #                                                 total_employees = employee_count
                #                                                 )
                IncrementDetailsSummary.objects.filter(company=company, department_team=department_team).update(total_employees = employee_count)
                print("CurrentPackageDetails")
                
        if sender is ProposedPackageDetails:
            # current_package = CurrentPackageDetails.objects.get(employee=instance.employee)
            # if current_package:
                # print("ProposedPackageDetails...")
                # # .update() prevents calling signal again
                # ProposedPackageDetails.objects.filter(id=instance.id).update(
                #     increased_amount=current_package.gross_salary * instance.increment_percentage,
                #     revised_salary=current_package.gross_salary + (current_package.gross_salary * instance.increment_percentage),
                #     revised_fuel_allowance=instance.increased_fuel_amount + current_package.fuel_limit
                # )

            print("ProposedPackageDetails")

            proposed_package = ProposedPackageDetails.objects.filter(employee__company=company, employee__department_team=department_team)
            if proposed_package.exists():
                increased_fuel_amount = proposed_package.aggregate(total_price=Sum('increased_fuel_amount'))['total_price'] or 0

                print("increased_fuel_amount: ",increased_fuel_amount)
                
                current_package = CurrentPackageDetails.objects.filter(employee__company=company, employee__department_team=department_team)
                if current_package.exists():
                    fuel_limit = current_package.aggregate(total_price=Sum('fuel_limit'))['total_price'] or 0
                else:
                    fuel_limit = 0

                print("fuel_limit: ",fuel_limit)

                IncrementDetailsSummary.objects.filter(company=company, 
                                                    department_team=department_team
                                                    ).update(total_employees = employee_count,
                                                                fuel_increment_impact_hod = increased_fuel_amount,
                                                                effective_fuel_percentage_hod = increased_fuel_amount/fuel_limit if fuel_limit>0 else None
                                                                )
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
                    # salary = proposed_package.increased_amount,
                    # gratuity = instance.salary/12,
                    # bonus = (instance.salary*Decimal(str(1.7)))/Decimal(str(12)),
                    # leave_encashment = instance.salary/12,
                    # mobile_allowance = proposed_package.mobile_allowance,
                    # fuel = proposed_package.increased_fuel_amount * Decimal(str(configuration.fuel_rate)),
                    # total = instance.salary + instance.gratuity + instance.bonus + instance.leave_encashment + instance.mobile_allowance + instance.fuel
                )

            financial_impact_per_month = FinancialImpactPerMonth.objects.filter(employee__company=company, employee__department_team=department_team)
            if financial_impact_per_month.exists():
                salary = financial_impact_per_month.aggregate(total_price=Sum('salary'))['total_price'] or 0

                # Increment_details_summary = IncrementDetailsSummary.objects.filter(company=company, department_team=department_team).first()
                # Increment_details_summary.total_employees = employee_count
                # Increment_details_summary.effective_increment_rate_hod = salary/Decimal(str(Increment_details_summary.current_salary))
                # Increment_details_summary.salary_increment_impact_hod = float(salary)
                # Increment_details_summary.total_cost_on_p_and_l_per_month = float(financial_impact_per_month.aggregate(total_price=Sum('total'))['total_price'] or 0)
                # Increment_details_summary.revised_department_salary = Increment_details_summary.salary_increment_impact_hod + Increment_details_summary.current_salary
                # Increment_details_summary.staff_revised_cost = Increment_details_summary.total_cost_on_p_and_l_per_month + Increment_details_summary.current_salary
                # Increment_details_summary.save()
                pass
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

def build_dependency_graph(formulas):
    graph = defaultdict(list)
    indegree = defaultdict(int)
    formula_targets = set()

    for formula in formulas:
        target = (formula.target_model.strip(), formula.target_field.strip().lower())
        formula_targets.add(target)   # ✅ keep track of only formula fields
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


def topological_sort(formulas):
    """
    Perform topological sort on formula dependencies.
    Returns the list of formula targets in correct evaluation order.
    """
    graph, indegree, formula_targets = build_dependency_graph(formulas)

    # Start queue with all zero indegree nodes
    queue = deque([node for node, deg in indegree.items() if deg == 0])
    order = []

    while queue:
        node = queue.popleft()

        # ✅ Only add real formula targets to the order
        if node in formula_targets:
            order.append(node)

        # Decrease indegree for dependent nodes
        for neighbor in graph[node]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)

    # ✅ Detect cycle (if some formulas never reduced indegree to 0)
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
