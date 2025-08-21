from .models import CurrentPackageDetails, ProposedPackageDetails, FinancialImpactPerMonth, IncrementDetailsSummary, configurations, Employee, hr_assigned_companies, DepartmentTeams
from django.db.models import Sum, Prefetch


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