from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.db import transaction


LOCAL_APPS = ['user']
                
def populate_default_formulas(sender, **kwargs):
    from .models import Formula, DepartmentTeams, FieldFormula, Company, FieldReference
    from django.apps import apps

    for app_config in apps.get_app_configs():
        all_models = apps.get_models()

        models = ["CurrentPackageDetails", "ProposedPackageDetails", "FinancialImpactPerMonth", "IncrementDetailsSummary", "Employee", "Configurations"]
        not_allowed_fields = ["mobile_provided", "vehicle", "resign", "approved", "is_deleted", "is_intern", "auto_mark_eligibility"]
        allowed_field_types = ["IntegerField", "DecimalField", "BooleanField", "FloatField"]
        for model in all_models:

            if model._meta.app_label in LOCAL_APPS and model.__name__ in models:

                # Get all field objects for the model
                fields = model._meta.get_fields()
                
                for field in fields:
                    if field.get_internal_type() not in allowed_field_types or field.name in not_allowed_fields:
                        continue
                    path = f'employee__{model.__name__.lower()}__{field.name}'

                    FieldReference.objects.update_or_create(
                        path=path,
                        defaults={
                            "model_name": model.__name__,
                            "field_name": field.name,
                            "display_name": field.name.replace('_', ' ').title(),
                        }
                    )
    
    # Default formula data
    default_formulas = [
        {
            "id": 2, "formula_name": "proposed revised salary",
            "formula_expression": "[CurrentPackageDetails: Gross Salary]+[ProposedPackageDetails: Increased Amount]",
            "target_model": "ProposedPackageDetails", "target_field": "revised_salary", "formula_is_default": True, "is_deleted": False
        },
        {
            "id": 9, "formula_name": "proposed total",
            "formula_expression": "[ProposedPackageDetails: Revised Salary]+[ProposedPackageDetails: Revised Fuel Allowance]",
            "target_model": "ProposedPackageDetails", "target_field": "total", "formula_is_default": True, "is_deleted": False
        },
        {
            "id": 8, "formula_name": "financial total",
            "formula_expression": "[FinancialImpactPerMonth: Salary]+[FinancialImpactPerMonth: Gratuity]+[FinancialImpactPerMonth: Bonus]+[FinancialImpactPerMonth: Leave Encashment]+[FinancialImpactPerMonth: Fuel]",
            "target_model": "FinancialImpactPerMonth", "target_field": "total", "formula_is_default": True, "is_deleted": False
        },
        {
            "id": 7, "formula_name": "financial fuel",
            "formula_expression": "[ProposedPackageDetails: Increased Fuel Allowance]",
            "target_model": "FinancialImpactPerMonth", "target_field": "fuel", "formula_is_default": True, "is_deleted": False
        },
        {
            "id": 6, "formula_name": "financial LE",
            "formula_expression": "[FinancialImpactPerMonth: Salary]/12",
            "target_model": "FinancialImpactPerMonth", "target_field": "leave_encashment", "formula_is_default": True, "is_deleted": False
        },
        {
            "id": 5, "formula_name": "financial bonus",
            "formula_expression": "[FinancialImpactPerMonth: Salary]*[Configurations: Bonus Constant Multiplier]/12",
            "target_model": "FinancialImpactPerMonth", "target_field": "bonus", "formula_is_default": True, "is_deleted": False
        },
        {
            "id": 4, "formula_name": "financial gratuity",
            "formula_expression": "[FinancialImpactPerMonth: Salary]/12",
            "target_model": "FinancialImpactPerMonth", "target_field": "gratuity", "formula_is_default": True, "is_deleted": False
        },
        {
            "id": 1, "formula_name": "proposed increased amount",
            "formula_expression": "[CurrentPackageDetails: Gross Salary]*([ProposedPackageDetails: Increment Percentage]/100)",
            "target_model": "ProposedPackageDetails", "target_field": "increased_amount", "formula_is_default": True, "is_deleted": False
        },
        {
            "id": 3, "formula_name": "financial salary",
            "formula_expression": "[ProposedPackageDetails: Increased Amount]",
            "target_model": "FinancialImpactPerMonth", "target_field": "salary", "formula_is_default": True, "is_deleted": False
        },
        {
            "id": 20, "formula_name": "summary staff revised cost",
            "formula_expression": "[IncrementDetailsSummary: Current Salary]+[IncrementDetailsSummary: Total Cost On P And L Per Month]",
            "target_model": "IncrementDetailsSummary", "target_field": "staff_revised_cost", "formula_is_default": True, "is_deleted": False
        },
        {
            "id": 19, "formula_name": "summary revised department salary",
            "formula_expression": "[IncrementDetailsSummary: Current Salary]+[IncrementDetailsSummary: Salary Increment Impact Hod]",
            "target_model": "IncrementDetailsSummary", "target_field": "revised_department_salary", "formula_is_default": True, "is_deleted": False
        },
        {
            "id": 18, "formula_name": "summary total cost on pand l per month",
            "formula_expression": "SUM[FinancialImpactPerMonth: Total]",
            "target_model": "IncrementDetailsSummary", "target_field": "total_cost_on_p_and_l_per_month", "formula_is_default": True, "is_deleted": False
        },
        {
            "id": 17, "formula_name": "summary other cost in p and l",
            "formula_expression": "[IncrementDetailsSummary: Total Cost On P And L Per Month] - [IncrementDetailsSummary: Salary Increment Impact Hod] - [IncrementDetailsSummary: Fuel Increment Impact Hod]",
            "target_model": "IncrementDetailsSummary", "target_field": "other_costs_in_p_and_l", "formula_is_default": True, "is_deleted": False
        },
        {
            "id": 16, "formula_name": "summary fuel increment impact hod",
            "formula_expression": "SUM[ProposedPackageDetails: Increased Fuel Allowance]",
            "target_model": "IncrementDetailsSummary", "target_field": "fuel_increment_impact_hod", "formula_is_default": True, "is_deleted": False
        },
        {
            "id": 15, "formula_name": "summary salary increment impact hod",
            "formula_expression": "SUM[FinancialImpactPerMonth: Salary]",
            "target_model": "IncrementDetailsSummary", "target_field": "salary_increment_impact_hod", "formula_is_default": True, "is_deleted": False
        },
        {
            "id": 14, "formula_name": "summary effective fuel impact hod",
            "formula_expression": "[IncrementDetailsSummary: Fuel Increment Impact Hod]/ SUM[CurrentPackageDetails: Fuel Allowance]",
            "target_model": "IncrementDetailsSummary", "target_field": "effective_fuel_percentage_hod", "formula_is_default": True, "is_deleted": False
        },
        {
            "id": 13, "formula_name": "summary current salary",
            "formula_expression": "SUM[CurrentPackageDetails: Gross Salary]",
            "target_model": "IncrementDetailsSummary", "target_field": "current_salary", "formula_is_default": True, "is_deleted": False
        },
        {
            "id": 12, "formula_name": "summary eligible for increment",
            "formula_expression": "SUM[Employee: Eligible For Increment]",
            "target_model": "IncrementDetailsSummary", "target_field": "eligible_for_increment", "formula_is_default": True, "is_deleted": False
        },
        {
            "id": 11, "formula_name": "salary increment hod",
            "formula_expression": "SUM[FinancialImpactPerMonth: Salary]/SUM[CurrentPackageDetails: Gross Salary]",
            "target_model": "IncrementDetailsSummary", "target_field": "effective_increment_rate_hod", "formula_is_default": True, "is_deleted": False
        },
        {
            "id": 10, "formula_name": "proposed fuel allowance",
            "formula_expression": "[ProposedPackageDetails: Increased Fuel Allowance] + [CurrentPackageDetails: Fuel Allowance]",
            "target_model": "ProposedPackageDetails", "target_field": "revised_fuel_allowance", "formula_is_default": True, "is_deleted": False
        },
        {
            "id": 21, "formula_name": "current package total",
            "formula_expression": "[CurrentPackageDetails: Gross Salary]+[CurrentPackageDetails: Fuel Allowance]",
            "target_model": "CurrentPackageDetails", "target_field": "total", "formula_is_default": True, "is_deleted": False
        }
    ]

    with transaction.atomic():
        # Step 1: Ensure all default formulas exist in the Formula model
        for formula_data in default_formulas:
            Formula.objects.update_or_create(
                id=formula_data["id"],
                defaults={
                    "formula_name": formula_data["formula_name"],
                    "formula_expression": formula_data["formula_expression"],
                    "target_model": formula_data["target_model"],
                    "target_field": formula_data["target_field"],
                    "formula_is_default": formula_data["formula_is_default"],
                    "is_deleted": formula_data["is_deleted"],
                }
            )

        # Step 2: Get all active departments and companies
        departments = DepartmentTeams.objects.filter(is_deleted=False)
        companies = Company.objects.all()

        # Step 3: Assign default formulas to departments without formulas
        default_formulas = Formula.objects.filter(formula_is_default=True, is_deleted=False)
        
        for company in companies:
            for department in departments.filter(company=company):
                # Check if the department has any FieldFormula assigned
                has_formulas = FieldFormula.objects.filter(
                    company=company, department_team=department
                ).exists()
                
                # If no formulas are assigned, assign all default formulas
                if not has_formulas:
                    for formula in default_formulas:
                        FieldFormula.objects.get_or_create(
                            formula=formula,
                            company=company,
                            department_team=department,
                            defaults={"description": f"Default formula: {formula.formula_name}"}
                        )

class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user'

    def ready(self):
        import user.signals
        # Connect the populate_default_formulas function to the post_migrate signal
        post_migrate.connect(populate_default_formulas, sender=self)
