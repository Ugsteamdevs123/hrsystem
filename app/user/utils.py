from .models import CurrentPackageDetails, ProposedPackageDetails, FinancialImpactPerMonth, IncrementDetailsSummary, configurations, Employee, hr_assigned_companies, DepartmentTeams
from django.db.models import Sum, Prefetch
from datetime import date


def update_department_team_increment_summary(sender, instance, company, department_team):
    employee_count = Employee.objects.filter(company=company, department_team=department_team).count()
    if sender is CurrentPackageDetails:
        current_package = CurrentPackageDetails.objects.filter(employee_company=company, emplyee_department_team=department_team)
        if current_package.exists():
            print("CurrentPackageDetails")
            gross_salary = current_package.aggregate(total_price=Sum('gross_salary'))['total_price'] or 0
            print("gross_salary: ", gross_salary)

            IncrementDetailsSummary.objects.filter(company=company, 
                                                   department_team=department_team
                                                   ).update(current_salary=gross_salary,
                                                            total_employees = employee_count
                                                            )
            print("CurrentPackageDetails")
            
    if sender is ProposedPackageDetails:
        current_package = CurrentPackageDetails.objects.get(employee=instance.employee)
        if current_package:
            print("ProposedPackageDetails")
            instance.increased_amount = current_package.gross_salary * instance.increment_percentage
            instance.revised_salary = current_package.gross_salary + instance.increased_amount
            instance.revised_fuel_allowance = instance.increased_fuel_amount + current_package.fuel_limit
            instance.save()
            print("ProposedPackageDetails")

            proposed_package = ProposedPackageDetails.objects.filter(employee_company=company, emplyee_department_team=department_team)
            if proposed_package.exists():
                increased_fuel_amount = proposed_package.aggregate(total_price=Sum('increased_fuel_amount'))['total_price'] or 0

                print("increased_fuel_amount: ",increased_fuel_amount)

                fuel_limit = CurrentPackageDetails.objects.filter(employee_company=company, emplyee_department_team=department_team).aaggregate(total_price=Sum('fuel_limit'))['total_price'] or 0

                print("fuel_limit: ",fuel_limit)

                IncrementDetailsSummary.objects.filter(company=company, 
                                                    department_team=department_team
                                                    ).update(total_employees = employee_count,
                                                                fuel_increment_impact_hod = increased_fuel_amount,
                                                                effective_fuel_percentage_hod = increased_fuel_amount/fuel_limit
                                                                )
                print("ProposedPackageDetails")

    if sender is FinancialImpactPerMonth:
        proposed_package = ProposedPackageDetails.objects.get(employee=instance.employee)
        configuration = configurations.objects.first()
        if proposed_package:
            years = configuration.as_of_date.year - instance.employee.date_of_joining.year
            if (configuration.as_of_date.month, configuration.as_of_date.day) < (instance.employee.date_of_joining.month, instance.employee.date_of_joining.day):
                years -= 1
                
            instance.serving_years = years
            instance.salary = proposed_package.increased_amount
            instance.gratuity = instance.salary/12
            instance.bonus = (instance.salary*1.7)/12
            instance.leave_encashment = instance.salary/12
            instance.mobile_allowance = proposed_package.mobile_allowance
            instance.fuel = proposed_package.increased_fuel_amount * configuration.fuel_rate
            instance.total = instance.salary + instance.gratuity + instance.bonus + instance.leave_encashment + instance.mobile_allowance + instance.fuel
            instance.save()

        financial_impact_per_month = FinancialImpactPerMonth.objects.filter(employee_company=company, emplyee_department_team=department_team)
        if financial_impact_per_month.exists():
            salary = financial_impact_per_month.aggregate(total_price=Sum('salary'))['total_price'] or 0

            Increment_details_summary = IncrementDetailsSummary.objects.filter(company=company, department_team=department_team).first()
            Increment_details_summary.total_employees = employee_count
            Increment_details_summary.effective_increment_rate_hod = salary/Increment_details_summary.current_salary
            Increment_details_summary.salary_increment_impact_hod = salary
            Increment_details_summary.total_cost_on_p_and_l_per_month = financial_impact_per_month.aggregate(total_price=Sum('total'))['total_price'] or 0
            Increment_details_summary.revised_department_salary = Increment_details_summary.salary_increment_impact_hod + Increment_details_summary.current_salary
            Increment_details_summary.staff_revised_cost = Increment_details_summary.total_cost_on_p_and_l_per_month + Increment_details_summary.current_salary
            Increment_details_summary.save()
            pass


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









# In app/utils.py
import re
from decimal import Decimal
from .models import FieldReference

def get_variables_from_expression(expression):
    """Extract field references like [CurrentPackageDetails: Gross Salary]."""
    pattern = r'\[(.*?): (.*?)\]'
    return re.findall(pattern, expression)  # Returns list of (model_name, display_name) tuples

def get_field_path(model_name, display_name):
    """Map display name to Django path."""
    try:
        ref = FieldReference.objects.get(model_name=model_name, display_name=display_name)
        return ref.path
    except FieldReference.DoesNotExist:
        raise ValueError(f"Field {model_name}: {display_name} not found")

def evaluate_formula(instance, expression):
    """Evaluate formula, replacing [Model: Field] with actual values."""
    variables = get_variables_from_expression(expression)
    context = {}
    for model_name, display_name in variables:
        path = get_field_path(model_name, display_name)
        try:
            value = get_nested_attr(instance, path)
            if isinstance(value, Decimal):
                value = float(value)  # For math ops
            context[f'[{model_name}: {display_name}]'] = value
        except AttributeError:
            raise ValueError(f"Invalid path for {model_name}: {display_name}")

    try:
        result = eval(expression, {"__builtins__": {}}, context)
        return Decimal(result)
    except Exception as e:
        raise ValueError(f"Formula evaluation failed: {e}")

def get_nested_attr(instance, path):
    parts = path.split('__')
    obj = instance
    for part in parts:
        obj = getattr(obj, part)
    return obj
