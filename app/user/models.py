from django.db import models
from django.utils.dateparse import parse_date
from django.contrib.auth.models import (
    AbstractBaseUser , 
    PermissionsMixin ,
    Group
)

from .managers import  CustomUserManager

from decimal import Decimal, InvalidOperation

# For audit logs 
from auditlog.registry import auditlog
from auditlog.models import AuditlogHistoryField
    
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation


class Gender(models.Model):
    gender = models.CharField(max_length=12)

    is_deleted = models.BooleanField(default=False)

    history = AuditlogHistoryField()  # Required to store log

    def __str__(self):
        return self.gender


class CustomUser(AbstractBaseUser , PermissionsMixin):
    email = models.EmailField(
        max_length=255 , 
        unique=True
    )
    full_name = models.CharField(max_length=255)
    gender = models.ForeignKey(
        Gender,
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    contact = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        unique=True
    )
    first_time_login_to_reset_pass = models.BooleanField(default=True)

    # for admin check
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    is_deleted = models.BooleanField(default=False)

    USERNAME_FIELD ='email'
    objects = CustomUserManager()

    history = AuditlogHistoryField()  # Required to store log

    @staticmethod
    def group_check(name: str) -> Group:
        designation, _ = Group.objects.get_or_create(name=name)
        return designation
    
    class Meta:
        permissions = [
            ('can_admin_access', 'Can Admin Access'),
            ('can_hr_level_access', 'Can HR Level Access')
        ]


class Company(models.Model):
    name = models.CharField(max_length=255)

    is_deleted = models.BooleanField(default=False)

    history = AuditlogHistoryField()  # Required to store log


    def __str__(self):
        return self.name


class hr_assigned_companies(models.Model):
    hr = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)

    is_deleted = models.BooleanField(default=False)

    history = AuditlogHistoryField()  # Required to store log

    def __str__(self):
        return self.hr.full_name + ' ' + self.company.name


class Designation(models.Model):
    title = models.CharField(max_length=255)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)

    is_deleted = models.BooleanField(default=False)

    history = AuditlogHistoryField()  # Required to store log

    def __str__(self):
        return self.title + ' ' + self.company.name


class DepartmentTeams(models.Model):
    name = models.CharField(max_length=255)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    is_deleted = models.BooleanField(default=False)

    history = AuditlogHistoryField()  # Required to store log


    def __str__(self):
        return self.name


class DepartmentGroups(models.Model):
    name = models.CharField(max_length=255)
    is_deleted = models.BooleanField(default=False)

    history = AuditlogHistoryField()  # Required to store log


    def __str__(self):
        return self.name


class Section(models.Model):
    name = models.CharField(max_length=255)
    department_group = models.ForeignKey(DepartmentGroups, on_delete=models.CASCADE, null=True)

    is_deleted = models.BooleanField(default=False)

    history = AuditlogHistoryField()  # Required to store log

    def __str__(self):
        return self.name


class EmployeeStatus(models.Model):
    status = models.CharField(max_length=255)
    is_deleted = models.BooleanField(default=False)

    history = AuditlogHistoryField()  # Required to store log

    def __str__(self):
        return self.status
    

class Formula(models.Model):
    formula_name = models.CharField(max_length=255)
    formula_expression = models.CharField(max_length=255)
    target_model = models.CharField(max_length=255, null=True, blank=True)  # e.g., 'ProposedPackageDetails'
    target_field = models.CharField(max_length=255, null=True, blank=True)  # e.g., 'revised_salary'
    formula_is_default = models.BooleanField(default=False)

    is_deleted = models.BooleanField(default=False)

    history = AuditlogHistoryField()  # Required to store log


    def __str__(self):
        return f"{self.target_model}.{self.target_field}: {self.formula_name}"
    

class Location(models.Model):
    location = models.CharField(max_length=122)
    code = models.CharField(max_length=50) 

    is_deleted = models.BooleanField(default=False)

    history = AuditlogHistoryField()  # Required to store log


class SummaryStatus(models.Model):
    approved = models.BooleanField(default=False)
    summary_submitted = models.BooleanField(default=False)

    is_deleted = models.BooleanField(default=False)

    history = AuditlogHistoryField()  # Required to store log

    def __str__(self):
        return 'Summary Approval Status: ' + str(self.approved)
        
class IncrementDetailsSummary(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    department_team = models.ForeignKey(DepartmentTeams, on_delete=models.CASCADE)
    total_employees = models.IntegerField(null=True)
    eligible_for_increment = models.IntegerField(null=True)
    current_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    effective_increment_rate_hod = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    effective_fuel_percentage_hod = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_increment_impact_hod = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fuel_increment_impact_hod = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    other_costs_in_p_and_l = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_cost_on_p_and_l_per_month = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    revised_department_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    staff_revised_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    approved = models.BooleanField(default=False)
    summaries_status = models.ForeignKey(SummaryStatus, on_delete=models.DO_NOTHING, null=True)

    is_deleted = models.BooleanField(default=False)

    history = AuditlogHistoryField()  # Required to store log

    def __str__(self):
        return self.department_team.company.name + ' ' + self.department_team.name + ' increment summary'


class IncrementDetailsSummaryDraft(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    department_team = models.ForeignKey(DepartmentTeams, on_delete=models.CASCADE)
    total_employees = models.IntegerField(null=True)
    eligible_for_increment = models.IntegerField(null=True)
    current_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    effective_increment_rate_hod = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    effective_fuel_percentage_hod = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_increment_impact_hod = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fuel_increment_impact_hod = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    other_costs_in_p_and_l = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_cost_on_p_and_l_per_month = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    revised_department_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    staff_revised_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    approved = models.BooleanField(default=False)
    summaries_status = models.ForeignKey(SummaryStatus, on_delete=models.DO_NOTHING, null=True)

    is_deleted = models.BooleanField(default=False)

    history = AuditlogHistoryField()  # Required to store log

    def __str__(self):
        return self.department_team.company.name + ' ' + self.department_team.name + ' increment summary'
    

class VehicleBrand(models.Model):
    """Stores vehicle brand details like Toyota, Honda."""
    name = models.CharField(max_length=50, unique=True)

    history = AuditlogHistoryField()  # Required to store log

    def __str__(self):
        return self.name


class VehicleModel(models.Model):
    # """Stores vehicle model details, linked to a brand."""

    brand = models.ForeignKey(VehicleBrand, on_delete=models.CASCADE, related_name='models')
    model_name = models.CharField(max_length=50)
    engine_cc = models.CharField(max_length=50) #For count cc

    history = AuditlogHistoryField()  # Required to store log

    def __str__(self):
        return f"{self.brand.name} {self.model_name} ({self.engine_cc})"
    


class DynamicAttributeDefinition(models.Model):
    DATA_TYPE_CHOICES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('boolean', 'Boolean'),
        ('date', 'Date'),
        # Add more types as needed
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    department_team = models.ForeignKey(DepartmentTeams, on_delete=models.CASCADE)
    key = models.CharField(max_length=100)
    display_name = models.CharField(max_length=255)  # Optional: for showing labels
    data_type = models.CharField(max_length=10, choices=DATA_TYPE_CHOICES)
    inline_editable = models.BooleanField(default=False)

    class Meta:
        unique_together = ('company', 'department_team', 'key')

    def __str__(self):
        return f"{self.key} - {self.data_type} ({self.department_team.name})"


class DynamicAttribute(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    definition = models.ForeignKey(DynamicAttributeDefinition, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    # key = models.CharField(max_length=100)
    value = models.TextField(default="0")

    @property
    def typed_value(self):
        """Return the value casted to the correct Python type."""
        try:
            if self.definition.data_type == 'number':
                return float(self.value)
            elif self.definition.data_type == 'boolean':
                return self.value.lower() in ['true', '1', 'yes']
            elif self.definition.data_type == 'date':
                return parse_date(self.value)
            return self.value  # default to string/text
        except Exception as e:
            print(f"Type conversion failed for {self.key}: {e}")
            return None
        
    def __str__(self):
        return f"{self.definition.key} ({self.definition.data_type}): {self.value}"


class Employee(models.Model):
    emp_id = models.IntegerField(unique=True)
    fullname = models.CharField(max_length=255)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    department_team = models.ForeignKey(DepartmentTeams, on_delete=models.CASCADE)
    department_group = models.ForeignKey(DepartmentGroups, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    designation = models.ForeignKey(Designation, on_delete=models.CASCADE)
    location = models.ForeignKey(Location , on_delete=models.CASCADE)
    date_of_joining = models.DateField()  # Date of Joining
    resign = models.BooleanField(default=False)
    date_of_resignation = models.DateField(blank=True, null=True)
    remarks = models.TextField(blank=True)
    image = models.FileField(upload_to='employee_images/', blank=True, null=True)
    eligible_for_increment = models.BooleanField(default=False)
    auto_mark_eligibility = models.BooleanField(default=True)
    is_intern = models.BooleanField(default=False)
    promoted_from_intern_date = models.DateField(blank=True, null=True)
    dynamic_attribute = GenericRelation(DynamicAttribute)

    is_deleted = models.BooleanField(default=False)
    history = AuditlogHistoryField()  # Required to store log

    @property
    def dynamic_fields(self):
        return {attr.definition.key: attr.value for attr in self.dynamic_attribute.all()}
    
    def set_dynamic_attribute(self, key, value):
        attr, created = DynamicAttribute.objects.update_or_create(
            content_type = ContentType.objects.get_for_model(self),
            definition = DynamicAttributeDefinition.objects.get(company = self.company, department_team=self.department_team, key=key),
            object_id = self.pk,
            # key = key,
            defaults={'value': str(value)}  # ✅ Correct place to update value
        )

        return attr, created
    
    def get_dynamic_attribute(self, key):
        return self.dynamic_attribute.get(key=key).value
        
    def __str__(self):
        return self.fullname


class CurrentPackageDetails(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE)
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2)
    vehicle = models.ForeignKey(VehicleModel, on_delete=models.SET_NULL, null=True)
    # fuel_limit = models.DecimalField(max_digits=10, decimal_places=2)

    mobile_provided = models.BooleanField(default=False)
    fuel_allowance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fuel_litre = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total = models.IntegerField(null=True, blank=True)

    company_pickup = models.BooleanField(default=False)

    is_deleted = models.BooleanField(default=False)

    history = AuditlogHistoryField()  # Required to store log

    def __str__(self):
        return f"Package for {self.employee.fullname}"

    def save(self, *args, **kwargs):
        # Handle only DecimalFields
        for field in self._meta.get_fields():
            if isinstance(field, models.DecimalField):
                val = getattr(self, field.name)
                if val == '' or val is None:  # empty string or None → store as 0
                    setattr(self, field.name, Decimal("0"))
                else:  # try converting to Decimal
                    try:
                        setattr(self, field.name, Decimal(val))
                    except (InvalidOperation, TypeError, ValueError):
                        setattr(self, field.name, Decimal("0"))

        # Everything else (CharField, ForeignKey, etc.) is saved as-is
        super().save(*args, **kwargs)


class ProposedPackageDetails(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE)
    increment_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    increased_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Changed from FK
    revised_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Changed from FK
    # increased_fuel_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    increased_fuel_allowance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    increased_fuel_litre = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    revised_fuel_allowance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Changed from FK
    vehicle = models.ForeignKey(VehicleModel, on_delete=models.SET_NULL, null=True)

    mobile_provided = models.BooleanField(default=False)
    total = models.IntegerField(null=True, blank=True)

    company_pickup = models.BooleanField(default=False)

    is_deleted = models.BooleanField(default=False)

    history = AuditlogHistoryField()  # Required to store log

    def __str__(self):
        return f"Proposed Package for {self.employee.fullname}"

    def save(self, *args, **kwargs):
        # Handle only DecimalFields
        for field in self._meta.get_fields():
            if isinstance(field, models.DecimalField):
                val = getattr(self, field.name)
                if val == '' or val is None:  # empty string or None → store as 0
                    setattr(self, field.name, Decimal("0"))
                else:  # try converting to Decimal
                    try:
                        setattr(self, field.name, Decimal(val))
                    except (InvalidOperation, TypeError, ValueError):
                        setattr(self, field.name, Decimal("0"))

        # Everything else (CharField, ForeignKey, etc.) is saved as-is
        super().save(*args, **kwargs)
    
    
    

class FinancialImpactPerMonth(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE)
    emp_status = models.ForeignKey(EmployeeStatus, on_delete=models.CASCADE, null=True, blank=True)
    serving_years = models.IntegerField(null=True, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    gratuity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Changed from FK
    bonus = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Changed from FK
    leave_encashment = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Changed from FK
    
    # mobile_provided = models.BooleanField(default=False)
    
    fuel = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    vehicle = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Changed from FK

    is_deleted = models.BooleanField(default=False)

    history = AuditlogHistoryField()  # Required to store log

    def __str__(self):
        return f"Final Impact for {self.employee.fullname}"

    def save(self, *args, **kwargs):
        # Handle only DecimalFields
        for field in self._meta.get_fields():
            if isinstance(field, models.DecimalField):
                val = getattr(self, field.name)
                if val == '' or val is None:  # empty string or None → store as 0
                    setattr(self, field.name, Decimal("0"))
                else:  # try converting to Decimal
                    try:
                        setattr(self, field.name, Decimal(val))
                    except (InvalidOperation, TypeError, ValueError):
                        setattr(self, field.name, Decimal("0"))

        # Everything else (CharField, ForeignKey, etc.) is saved as-is
        super().save(*args, **kwargs)
        
    
from django.db import models
from decimal import Decimal
from django.core.exceptions import ValidationError
from auditlog.models import AuditlogHistoryField

class EmployeeDraft(models.Model):
    emp_id = models.IntegerField(unique=True)
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='drafts')

    fullname = models.CharField(max_length=255, blank=True, null=True)
    company = models.ForeignKey('Company', on_delete=models.CASCADE, null=True, blank=True)
    department_team = models.ForeignKey('DepartmentTeams', on_delete=models.CASCADE, null=True, blank=True)
    department_group = models.ForeignKey('DepartmentGroups', on_delete=models.CASCADE, null=True, blank=True)
    section = models.ForeignKey('Section', on_delete=models.CASCADE, null=True, blank=True)
    designation = models.ForeignKey('Designation', on_delete=models.CASCADE, null=True, blank=True)
    location = models.ForeignKey('Location', on_delete=models.CASCADE, null=True, blank=True)
    date_of_joining = models.DateField(blank=True, null=True)
    resign = models.BooleanField(default=False, null=True)
    date_of_resignation = models.DateField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    image = models.FileField(upload_to='employee_draft_images/', blank=True, null=True)
    eligible_for_increment = models.BooleanField(default=False, null=True)
    auto_mark_eligibility = models.BooleanField(default=True, null=True)
    is_intern = models.BooleanField(default=False, null=True)
    promoted_from_intern_date = models.DateField(blank=True, null=True)
    dynamic_attribute = GenericRelation(DynamicAttribute)

    is_deleted = models.BooleanField(default=False)
    edited_fields = models.JSONField(default=dict, blank=True)

    history = AuditlogHistoryField()

    @property
    def dynamic_fields(self):
        return {attr.key: attr.value for attr in self.dynamic_attribute.all()}
    
    def set_dynamic_attribute(self, key, value):
        attr, created = DynamicAttribute.objects.update_or_create(
            content_type = ContentType.objects.get_for_model(self),
            definition = DynamicAttributeDefinition.objects.get(company = self.company, department_team=self.department_team, key=key),
            # key=key,
            object_id = self.pk,
            defaults={'value': str(value)}  # ✅ Correct place to update value
        )

        return attr, created
    
    def get_dynamic_attribute(self, key):
        return self.dynamic_attribute.get(key=key).value

    def __str__(self):
        return f"Draft for {self.employee.fullname}"

    # def save(self, *args, **kwargs):
    #     # Ensure at least one field is edited
    #     if not self.edited_fields and not self.pk:
    #         raise ValidationError("At least one field must be edited to create a draft.")
    #     super().save(*args, **kwargs)

    # def save(self, *args, **kwargs):
    #     """
    #     Custom save method that enforces edited_fields on create,
    #     but allows bypassing validation with `validate=False`.
    #     """
    #     validate = kwargs.pop('validate', True)
    #     print("validate: ", validate)
    #     if validate and not self.edited_fields and not self.pk:
    #         raise ValidationError("At least one field must be edited to create a draft.")
    #     super().save(*args, **kwargs)

class CurrentPackageDetailsDraft(models.Model):
    employee_draft = models.OneToOneField(EmployeeDraft, on_delete=models.CASCADE)
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    vehicle = models.ForeignKey('VehicleModel', on_delete=models.SET_NULL, null=True, blank=True)
    # fuel_limit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    mobile_provided = models.BooleanField(default=False, null=True)
    fuel_litre = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fuel_allowance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total = models.IntegerField(null=True, blank=True)
    company_pickup = models.BooleanField(default=False, null=True)

    is_deleted = models.BooleanField(default=False)
    edited_fields = models.JSONField(default=dict, blank=True)

    history = AuditlogHistoryField()

    def __str__(self):
        return f"Current Package Draft for {self.employee_draft.employee.fullname}"

    def save(self, *args, **kwargs):
        for field in self._meta.get_fields():
            if isinstance(field, models.DecimalField):
                val = getattr(self, field.name)
                if val == '' or val is None:
                    setattr(self, field.name, Decimal("0"))
                else:
                    try:
                        setattr(self, field.name, Decimal(val))
                    except (InvalidOperation, TypeError, ValueError):
                        setattr(self, field.name, Decimal("0"))
        super().save(*args, **kwargs)

class ProposedPackageDetailsDraft(models.Model):
    employee_draft = models.OneToOneField(EmployeeDraft, on_delete=models.CASCADE)
    increment_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    increased_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    revised_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # increased_fuel_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    increased_fuel_litre = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    increased_fuel_allowance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    revised_fuel_allowance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    vehicle = models.ForeignKey('VehicleModel', on_delete=models.SET_NULL, null=True, blank=True)
    mobile_provided = models.BooleanField(default=False, null=True)
    total = models.IntegerField(null=True, blank=True)
    company_pickup = models.BooleanField(default=False, null=True)

    is_deleted = models.BooleanField(default=False)
    edited_fields = models.JSONField(default=dict, blank=True)

    history = AuditlogHistoryField()

    def __str__(self):
        return f"Proposed Package Draft for {self.employee_draft.employee.fullname}"

    def save(self, *args, **kwargs):
        for field in self._meta.get_fields():
            if isinstance(field, models.DecimalField):
                val = getattr(self, field.name)
                if val == '' or val is None:
                    setattr(self, field.name, Decimal("0"))
                else:
                    try:
                        setattr(self, field.name, Decimal(val))
                    except (InvalidOperation, TypeError, ValueError):
                        setattr(self, field.name, Decimal("0"))
        super().save(*args, **kwargs)



class FinancialImpactPerMonthDraft(models.Model):
    employee_draft = models.OneToOneField(EmployeeDraft, on_delete=models.CASCADE)
    emp_status = models.ForeignKey('EmployeeStatus', on_delete=models.CASCADE, null=True, blank=True)
    serving_years = models.IntegerField(null=True, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    gratuity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    bonus = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    leave_encashment = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fuel = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    vehicle = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    is_deleted = models.BooleanField(default=False)
    edited_fields = models.JSONField(default=dict, blank=True)

    history = AuditlogHistoryField()

    def __str__(self):
        return f"Financial Impact Draft for {self.employee_draft.employee.fullname}"

    def save(self, *args, **kwargs):
        for field in self._meta.get_fields():
            if isinstance(field, models.DecimalField):
                val = getattr(self, field.name)
                if val == '' or val is None:
                    setattr(self, field.name, Decimal("0"))
                else:
                    try:
                        setattr(self, field.name, Decimal(val))
                    except (InvalidOperation, TypeError, ValueError):
                        setattr(self, field.name, Decimal("0"))
        super().save(*args, **kwargs)
        

class Configurations(models.Model):
    fuel_rate = models.FloatField(null=True)
    as_of_date = models.DateField(null=True)
    bonus_constant_multiplier = models.FloatField(null=True)

    is_deleted = models.BooleanField(default=False)

    history = AuditlogHistoryField()  # Required to store log

    def __str__(self):
        return f"{self.fuel_rate} - {self.as_of_date} - {self.bonus_constant_multiplier}"


class FieldFormula(models.Model):
    formula = models.ForeignKey(Formula, on_delete=models.CASCADE, null=True, blank=True, default=None)
    description = models.TextField(blank=True)  # Optional help text
    # employee = models.ForeignKey(
    #     Employee,
    #     on_delete=models.CASCADE,
    #     null=True,
    #     blank=True,
    #     help_text="Optional: Formula applies to this employee only."
    # )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        help_text="Required: Formula applies to this company."
    )

    department_team = models.ForeignKey(
        DepartmentTeams,
        on_delete=models.CASCADE,
        help_text="Required if no employee: Formula applies to this department team."
    )

    history = AuditlogHistoryField()  # Required to store log

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(models.Q(department_team__isnull=False)),
                name='department_required'
            )
        ]

    def __str__(self):
        scope = self.department_team or "Global"
        return f"{self.formula} ({scope})"


class FieldReference(models.Model):
    MODEL_CHOICES = [
        ('CurrentPackageDetails', 'Current Package Details'),
        ('ProposedPackageDetails', 'Proposed Package Details'),
        ('FinancialImpactPerMonth', 'Financial Impact Per Month'),
        ('IncrementDetailsSummary', 'Increment Details Summary'),
        ('CurrentPackageDetailsDraft', 'Current Package Details Draft'),
        ('ProposedPackageDetailsDraft', 'Proposed Package Details Draft'),
        ('FinancialImpactPerMonthDraft', 'Financial Impact Per Month Draft'),
        ('IncrementDetailsSummaryDraft', 'Increment Details Summary Draft'),
        ('Employee', 'Employee'),
        ('Configurations', 'Configurations')
    ]

    model_name = models.CharField(max_length=255, choices=MODEL_CHOICES)
    field_name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    path = models.CharField(max_length=255)

    history = AuditlogHistoryField()  # Required to store log

    class Meta:
        unique_together = ('model_name', 'field_name')

    def __str__(self):
        return f"{self.model_name}: {self.display_name}"







# 4️⃣ Access dynamic attributes
# for attr in product.dynamic_attributes.all():
#     print(attr.key, attr.value)

# # Or access one specific field
# warranty = product.dynamic_attributes.filter(key="warranty_period").first()
# print(warranty.value)  # Output: 2 years

# 🚀 Optional: Access as Dictionary

# You can write a helper method on your Product model to get dynamic fields easily:

# class Product(models.Model):
#     name = models.CharField(max_length=100)
#     dynamic_attributes = GenericRelation('DynamicAttribute')

#     def get_dynamic_dict(self):
#         return {attr.key: attr.value for attr in self.dynamic_attributes.all()}


# Now use it like:

# fields = product.get_dynamic_dict()
# print(fields["origin_country"])  # Output: Germany
