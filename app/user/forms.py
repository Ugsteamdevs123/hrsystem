# In app/forms.py
from django import forms
from django.apps import apps
from django.contrib.auth.models import Group

from .utils import iter_allowed_models, get_model_by_name, list_fields

from .models import (
    Company , 
    CustomUser , 
    Section,
    DepartmentGroups,
    hr_assigned_companies,
    VehicleBrand,
    VehicleModel,
    Formula, 
    FieldFormula,
    FieldReference,
    Employee,
    DepartmentTeams
)


class FormulaForm(forms.ModelForm):

    class Meta:
        model = Formula
        fields = ['formula_name', 'formula_expression']
        widgets = {
            'formula_expression': forms.Textarea(attrs={'rows': 4, 'id': 'formula-expression'}),
        }


class FieldFormulaForm(forms.ModelForm):
    target_field = forms.ChoiceField(choices=[], required=True)
    company = forms.ModelChoiceField(
        queryset=Company.objects.none(),  # Will be set dynamically
        required=True,
        empty_label="Select a company",
        help_text="Choose the company for this formula."
    )
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.all(),
        required=False,
        empty_label="Select an employee (optional)",
        help_text="Choose an employee for a specific formula, or leave blank for department-wide."
    )
    department_team = forms.ModelChoiceField(
        queryset=DepartmentTeams.objects.all(),
        required=False,
        empty_label="Select a department team",
        help_text="Choose a department team (required if no employee is selected)."
    )

    class Meta:
        model = FieldFormula
        fields = ['target_model', 'target_field', 'formula', 'company', 'department_team', 'employee', 'description']
        widgets = {
            'target_model': forms.Select(
                choices=[
                    ('', 'Select a model'),
                    ('ProposedPackageDetails', 'Proposed Package Details'),
                    ('FinancialImpactPerMonth', 'Financial Impact Per Month'),
                    ('IncrementDetailsSummary', 'Increment Details Summary'),
                ],
                attrs={'required': 'true'}
            ),
            'target_field': forms.Select(attrs={'required': 'true'}),
            'formula': forms.Select(attrs={'required': 'true'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, user=None, *args, **kwargs):  # Add user parameter
        super().__init__(*args, **kwargs)
        self.user = user

        # Filter companies by hr_assigned_companies
        if self.user:
            assigned_companies = hr_assigned_companies.objects.filter(hr=self.user).values('company')
            self.fields['company'].queryset = Company.objects.filter(id__in=assigned_companies)

        # Filter target_field based on target_model
        model_name = self.data.get('target_model') if 'target_model' in self.data else (self.instance.target_model if self.instance.pk else None)
        if model_name:
            try:
                model = apps.get_model("user", model_name)
                fields = [f.name for f in model._meta.get_fields() if not f.is_relation]
                self.fields['target_field'].choices = [(f, f.replace('_', ' ').title()) for f in fields]
            except LookupError:
                self.fields['target_field'].choices = []

        # Filter department_team and employee based on company
        company_id = self.data.get('company') if 'company' in self.data else (self.instance.company_id if self.instance.pk else None)
        if company_id:
            self.fields['department_team'].queryset = DepartmentTeams.objects.filter(company_id=company_id)
            self.fields['employee'].queryset = Employee.objects.filter(company_id=company_id)
        else:
            self.fields['department_team'].queryset = DepartmentTeams.objects.none()
            self.fields['employee'].queryset = Employee.objects.none()

        # Filter employee based on department_team
        department_team_id = self.data.get('department_team') if 'department_team' in self.data else (self.instance.department_team_id if self.instance.pk else None)
        if department_team_id and company_id:
            self.fields['employee'].queryset = Employee.objects.filter(
                company_id=company_id,
                department_team_id=department_team_id
            )

        self.fields['target_model'].required = True
        self.fields['formula'].required = True
        self.fields['company'].required = True

    def clean(self):
        cleaned_data = super().clean()
        employee = cleaned_data.get('employee')
        department_team = cleaned_data.get('department_team')
        company = cleaned_data.get('company')
        if not company:
            raise forms.ValidationError("A company must be selected.")
        if not employee and not department_team:
            raise forms.ValidationError("Either an employee or a department team must be selected.")
        if employee and employee.company != company:
            raise forms.ValidationError("Selected employee must belong to the selected company.")
        if department_team and department_team.company != company:
            raise forms.ValidationError("Selected department team must belong to the selected company.")
        if employee and department_team and employee.department_team != department_team:
            raise forms.ValidationError("Selected employee must belong to the selected department team.")
        return cleaned_data
    
    # def save(self, commit=True):
    #     print("Values before saving:", self.cleaned_data)  # Inspect values
    #     return super().save(commit)            


class FieldReferenceAdminForm(forms.ModelForm):
    # keep as ChoiceField so admin shows dropdowns
    model_name = forms.ChoiceField(choices=[], required=True)
    field_name = forms.ChoiceField(choices=[], required=True)

    class Meta:
        model = FieldReference
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 1) Model choices (from allowed apps)
        model_choices = [(m.__name__, m.__name__) for _, m in iter_allowed_models()]
        model_choices.sort(key=lambda x: x[0].lower())
        self.fields["model_name"].choices = [("", "Select a model…")] + model_choices

        # 2) Determine which model is selected for this request
        selected_model = self.data.get("model_name") or (self.instance.model_name if self.instance.pk else None)

        # 3) Build field choices for the selected model (server-side, for validation)
        if selected_model:
            _, model_cls = get_model_by_name(selected_model)
            allowed = list_fields(model_cls)
            choices = [("", "Select a field…")] + [(f, f) for f in allowed]
            self.fields["field_name"].choices = choices

            # Guard: if POSTed field was populated via JS but choices weren’t yet built,
            # temporarily add it so we avoid the generic “Select a valid choice …” error.
            posted_field = self.data.get("field_name")
            if posted_field and posted_field not in allowed:
                self.fields["field_name"].choices += [(posted_field, posted_field)]
        else:
            self.fields["field_name"].choices = [("", "Select a field…")]

    def clean_field_name(self):
        field = self.cleaned_data.get("field_name")
        model_name = self.cleaned_data.get("model_name") or self.data.get("model_name")
        _, model_cls = get_model_by_name(model_name)
        allowed = list_fields(model_cls)
        if field not in allowed:
            # Clear, precise error instead of the generic one.
            raise forms.ValidationError(f"'{field}' is not a valid field on {model_name}.")
        return field

    def save(self, commit=True):
        obj = super().save(commit=False)
        # Auto-fill display_name
        if obj.field_name and not obj.display_name:
            obj.display_name = obj.field_name.replace("_", " ").title()
        # Auto-fill path with the employee__ prefix (as you wanted)
        if obj.model_name and obj.field_name:
            obj.path = f"employee__{obj.model_name.lower()}__{obj.field_name}"
        if commit:
            obj.save()
        return obj


class CustomUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    groups = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=False,
        empty_label="Select Group",
        label="Assign Group"
    )

    class Meta:
        model = CustomUser
        fields = ["full_name", "email", "password", "gender", "contact", "groups"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])  # Hash password properly
        if commit:
            user.save()
            if self.cleaned_data["groups"]:
                user.groups.add(self.cleaned_data["groups"])  # Assign group
        return user


class CustomUserUpdateForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        label="Password",
        required=False  # ✅ optional here
    )

    groups = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=False,
        empty_label="Select Group",
        label="Assign Group"
    )

    class Meta:
        model = CustomUser
        fields = ['full_name', 'email', 'password', 'gender', 'contact' , 'groups']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Number'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-select the current group if user has one
        if self.instance and self.instance.pk:
            user_groups = self.instance.groups.first()  # assuming one group per user
            if user_groups:
                self.fields['groups'].initial = user_groups

    def save(self, commit=True):
        user = super().save(commit=False)

        print("DEBUG: Entered save() for user:", user.email)
        print("Selected group:", self.cleaned_data.get("groups"))

        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])

        if commit:
            user.save()  # ensure user is in DB
            user.groups.set([])  # clears old groups safely
            if self.cleaned_data.get("groups"):
                user.groups.add(self.cleaned_data["groups"])
            print("Groups after save:", list(user.groups.all()))

        return user


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter Company Name', 'class': 'form-control'})
        }

        
class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ['name', 'department_group']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Enter Section Name',
                'class': 'form-control'
            }),
            'department_group': forms.Select(attrs={
                'class': 'form-control'
            })
        }
        labels = {
            'name': 'Section Name',
            'department_group': 'Department Group'
        }



class DepartmentGroupsForm(forms.ModelForm):
    class Meta:
        model = DepartmentGroups
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Enter Department Group Name',
                'class': 'form-control'
            })
        }


class HrAssignedCompaniesForm(forms.ModelForm):
    hr = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(is_active=True, is_superuser=False),
        label="HR",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select HR"
    )

    class Meta:
        model = hr_assigned_companies
        fields = ['hr', 'company']
        widgets = {
            'company': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Display full_name instead of email
        self.fields['hr'].label_from_instance = lambda obj: obj.full_name


class VehicleModelForm(forms.ModelForm):
    new_brand = forms.CharField(max_length=50, required=False, label="New Brand Name")

    class Meta:
        model = VehicleModel
        fields = ["brand", "model_name", "vehicle_type"]

    def clean(self):
        cleaned_data = super().clean()
        brand = cleaned_data.get("brand")
        new_brand = cleaned_data.get("new_brand")
        brand_option = self.data.get("brand_option")

        # Debugging log
        print(f"Cleaning form: brand_option={brand_option}, brand={brand}, new_brand={new_brand}")

        if brand_option == "new":
            if not new_brand:
                self.add_error("new_brand", "New brand name is required when adding a new brand.")
            else:
                # Create or get the brand and set it in cleaned_data
                brand, created = VehicleBrand.objects.get_or_create(name=new_brand.strip())
                cleaned_data["brand"] = brand
                # Clear any errors on the brand field to avoid "required" error
                if "brand" in self.errors:
                    del self.errors["brand"]
        elif brand_option == "existing" and not brand:
            self.add_error("brand", "Please select an existing brand.")

        return cleaned_data


class VehicleBrandForm(forms.ModelForm):
    class Meta:
        model = VehicleBrand
        fields = ["name"]