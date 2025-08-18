from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser , 
    PermissionsMixin ,
    Group
)
from .managers import  CustomUserManager

# Create your models here.


class Gender(models.Model):
    gender = models.CharField(max_length=12)

class CustomUser(AbstractBaseUser , PermissionsMixin):
    email = models.EmailField(
        max_length=255 , 
        unique=True
    )
    full_name = models.CharField(max_length=255)

    # # For making relation with django built-in Group
    # designation =  models.ForeignKey(
    #     Group, 
    #     on_delete=models.CASCADE,
    # )

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

    # for admin check
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)


    USERNAME_FIELD ='email'
    objects = CustomUserManager()

    @staticmethod
    def group_check(name: str) -> Group:
        designation, _ = Group.objects.get_or_create(name=name)
        return designation




class Company(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Designation(models.Model):
    title = models.CharField(max_length=255)

    def __str__(self):
        return self.title


class Department(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Section(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class EmployeeStatus(models.Model):
    status = models.CharField(max_length=255)

    def __str__(self):
        return self.status
    
class Formula(models.Model):
    formula_name = models.CharField(max_length=255)
    formula_expression = models.CharField(max_length=255)

    def __str__(self):
        return self.formula_name
    
class Location(models.Model):
    location = models.CharField(max_length=122)
    code = models.CharField(max_length=50) 

    


class Employee (models.Model):

    emp_id = models.AutoField(primary_key=True)
    fullname = models.CharField(max_length=255)
    company_name = models.ForeignKey(Company, on_delete=models.CASCADE)
    designation = models.ForeignKey(Designation, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    
    location = models.ForeignKey(Location , on_delete=models.CASCADE)
    date_of_joining = models.DateField()  # Date of Joining

    resign = models.BooleanField(default=False)
    date_of_resignation = models.DateField(blank=True, null=True)

    remarks = models.TextField(blank=True)
    image = models.FileField(upload_to='employee_images/', blank=True, null=True)

    def __str__(self):
        return self.fullname


class CurrentPackageDetails(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE)
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2)
    vehicle = models.DecimalField(max_digits=10, decimal_places=2)
    fuel_limit = models.DecimalField(max_digits=10, decimal_places=2)
    mobile_allowance = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Package for {self.employee.fullname}"


class ProposedPackageDetails(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE)
    increment_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    increased_amount = models.ForeignKey(Formula, related_name='increased_amount', on_delete=models.SET_NULL, null=True)
    revised_salary = models.ForeignKey(Formula, related_name='revised_salary', on_delete=models.SET_NULL, null=True)
    increased_fuel_amount = models.DecimalField(max_digits=10, decimal_places=2)
    revised_fuel_allowance = models.ForeignKey(Formula, related_name='revised_fuel_allowance', on_delete=models.SET_NULL, null=True)
    mobile_allowance = models.DecimalField(max_digits=10, decimal_places=2)
    vehicle = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Proposed Package for {self.employee.fullname}"
    
class FinancialImpactPerMonth(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE)
    emp_status = models.ForeignKey(EmployeeStatus, on_delete=models.CASCADE)
    serving_years = models.IntegerField()
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    gratuity = models.ForeignKey(Formula, related_name='gratuity', on_delete=models.SET_NULL, null=True)
    bonus = models.ForeignKey(Formula, related_name='bonus', on_delete=models.SET_NULL, null=True)
    leave_encashment = models.ForeignKey(Formula, related_name='le', on_delete=models.SET_NULL, null=True)
    mobile_allowance = models.ForeignKey(Formula, related_name='mobile_allowance', on_delete=models.SET_NULL, null=True)
    fuel = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.ForeignKey(Formula, related_name='total', on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Final Impact for {self.employee.fullname}"






