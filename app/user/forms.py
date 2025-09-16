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
    DepartmentTeams,
    Configurations
)


from django.core.exceptions import ValidationError

class FormulaForm(forms.ModelForm):

    class Meta:
        model = Formula
        fields = ['formula_name', 'formula_expression', 'target_model', 'target_field']
        widgets = {
            'formula_expression': forms.Textarea(attrs={'rows': 4, 'id': 'formula-expression'}),
            # 'formula_is_default': forms.Select(
            #     choices=[
            #         ('', 'Select a Choice'),
            #         ('True', 'Yes'),
            #         ('False', 'No'),
            #     ],
            #     attrs={'required': 'true'}
            # ),
            'target_model': forms.Select(
                choices=[
                    ('', 'Select a model'),
                    ('CurrentPackageDetails', 'Current Package Details'),
                    ('ProposedPackageDetails', 'Proposed Package Details'),
                    ('FinancialImpactPerMonth', 'Financial Impact Per Month'),
                    ('IncrementDetailsSummary', 'Increment Details Summary'),
                ],
                attrs={'required': 'true'}
            ),
            'target_field': forms.Select(attrs={'required': 'true'}),
        }


class FieldFormulaForm(forms.ModelForm):
    # company = forms.ModelChoiceField(
    #     queryset=Company.objects.none(),  # Will be set dynamically
    #     required=True,
    #     empty_label="Select a company",
    #     help_text="Choose the company for this formula."
    # )
    department_team = forms.ModelChoiceField(
        queryset=DepartmentTeams.objects.all(),
        required=False,
        empty_label="Select a department team",
        help_text="Choose a department team (required if no employee is selected)."
    )

    class Meta:
        model = FieldFormula
        fields = ['formula', 'company', 'department_team', 'description']
        # fields = ['formula', 'department_team', 'description']
        widgets = {
            'formula': forms.Select(attrs={'required': 'true'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    # def __init__(self, user=None, *args, **kwargs):  # Add user parameter
    #     super().__init__(*args, **kwargs)
    #     self.user = user

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.user = user

        # Filter companies by hr_assigned_companies
        # if self.user:
        #     assigned_companies = hr_assigned_companies.objects.filter(hr=self.user).values('company')
        #     self.fields['company'].queryset = Company.objects.filter(id__in=assigned_companies)

        # # Filter department_team and employee based on company
        # company_id = self.data.get('company') if 'company' in self.data else (self.instance.company_id if self.instance.pk else None)
        # if company_id:
        #     self.fields['department_team'].queryset = DepartmentTeams.objects.filter(company_id=company_id)
        # else:
        #     self.fields['department_team'].queryset = DepartmentTeams.objects.none()
            
        # self.fields['formula'].required = True
        # self.fields['company'].required = True

    def clean(self):
        cleaned_data = super().clean()
        department_team = cleaned_data.get('department_team')
        company = cleaned_data.get('company')
        print("checking: ", department_team, company, cleaned_data)
        if not company:
            print("1")
            raise forms.ValidationError("A company must be selected.")
        if not department_team:
            print("2")
            raise forms.ValidationError("A department must be selected.")
        if department_team and department_team.company != company:
            print("4")
            raise forms.ValidationError("Selected department team must belong to the selected company.")
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

        # Debugging: Log raw POST data and form state
        print("INIT: Raw POST data:", dict(self.data))
        print("INIT: Form instance PK:", self.instance.pk if self.instance else None)

        # 1) Set model choices
        model_choices = [(m.__name__, m.__name__) for _, m in iter_allowed_models()]
        model_choices.sort(key=lambda x: x[0].lower())
        self.fields["model_name"].choices = [("", "Select a model…")] + model_choices
        print("INIT: model_name choices:", self.fields["model_name"].choices)

        # Store choices to ensure they persist
        self._model_choices = self.fields["model_name"].choices

        # 2) Determine selected model
        selected_model = self.data.get("model_name") or (self.instance.model_name if self.instance.pk else None)
        print("INIT: Selected model:", selected_model)

        # 3) Build field choices
        if selected_model:
            try:
                _, model_cls = get_model_by_name(selected_model)
                allowed = list_fields(model_cls)
                choices = [("", "Select a field…")] + [(f, f) for f in allowed]
                self.fields["field_name"].choices = choices
                print("INIT: field_name choices for", selected_model, ":", choices)

                # Guard: Handle dynamically posted field_name
                posted_field = self.data.get("field_name")
                if posted_field and posted_field not in allowed:
                    self.fields["field_name"].choices += [(posted_field, posted_field)]
                    print("INIT: Added posted field to choices:", posted_field)
            except Exception as e:
                print(f"INIT: Error getting model/fields for {selected_model}: {e}")
        else:
            self.fields["field_name"].choices = [("", "Select a field…")]
            print("INIT: No selected model, field_name choices:", self.fields["field_name"].choices)

    def clean(self):
        print("CLEAN: Starting form clean method")
        print("CLEAN: model_name choices:", self.fields["model_name"].choices)
        print("CLEAN: cleaned_data before super:", self.cleaned_data)
        cleaned_data = super().clean()
        print("CLEAN: cleaned_data after super:", cleaned_data)
        return cleaned_data

    def clean_model_name(self):
        model_name = self.cleaned_data.get("model_name")
        print("CLEAN_MODEL_NAME: Input model_name:", model_name)
        print("CLEAN_MODEL_NAME: Available choices:", self._model_choices)

        if not model_name:
            raise ValidationError("Model name is required.")

        model_choices = [m[0] for m in self._model_choices]
        if model_name not in model_choices:
            raise ValidationError(f"'{model_name}' is not a valid model name. Choices are: {model_choices}")

        return model_name

    def clean_field_name(self):
        field = self.cleaned_data.get("field_name")
        model_name = self.cleaned_data.get("model_name")
        print("CLEAN_FIELD_NAME: field:", field, "model_name:", model_name)
        print("CLEAN_FIELD_NAME: cleaned_data:", self.cleaned_data)

        if not model_name:
            raise ValidationError("A valid model name must be selected.")

        try:
            _, model_cls = get_model_by_name(model_name)
            allowed = list_fields(model_cls)
            print("CLEAN_FIELD_NAME: Allowed fields for", model_name, ":", allowed)
            if field not in allowed:
                raise ValidationError(f"'{field}' is not a valid field on {model_name}.")
            print("CLEAN_FIELD_NAME: Allowed fields forddddddddd")
        except Exception as e:
            raise ValidationError(f"Error validating field for model {model_name}: {e}")
        print("CLEAN_FIELD_NAME: Allowed fields forghfjhgjgh")
        return field

    def save(self, commit=True):
        print("SAVE: Saving FieldReference...")
        obj = super().save(commit=False)
        if obj.field_name and not obj.display_name:
            obj.display_name = obj.field_name.replace("_", " ").title()
        if obj.model_name and obj.field_name:
            obj.path = f"employee__{obj.model_name.lower()}__{obj.field_name}"
        if commit:
            obj.save()
        print("SAVE: Saved object:", obj)
        return obj


class CustomUserForm(forms.ModelForm):
    # password = forms.CharField(widget=forms.PasswordInput)
    groups = forms.ModelChoiceField(
        queryset=Group.objects.exclude(name='Admin'),
        required=False,
        empty_label="Select Group",
        label="Assign Group"
    )

    class Meta:
        model = CustomUser
        fields = [
            "full_name", 
            "email", 
            # "password", 
            "gender", 
            "contact", 
            "groups"
        ]

    def save(self, commit=True):
        full_name = self.cleaned_data["full_name"]
        email = self.cleaned_data["email"]
        gender = self.cleaned_data["gender"]
        contact = self.cleaned_data["contact"]
        group = self.cleaned_data.get("groups")

        # ✅ Call manager method instead of model.save()
        user = CustomUser.objects.create_user(
            full_name=full_name,
            email=email,
            gender=gender,
            contact=contact,
        )

        if group:
            user.groups.add(group)

        return user

    # def save(self, commit=True):
    #     user = super().save(commit=False)
    #     # user.set_password(self.cleaned_data["password"])  # Hash password properly
    #     if commit:
    #         user.save()
    #         if self.cleaned_data["groups"]:
    #             user.groups.add(self.cleaned_data["groups"])  # Assign group
    #     return user


class CustomUserUpdateForm(forms.ModelForm):
    # password = forms.CharField(
    #     widget=forms.PasswordInput,
    #     label="Password",
    #     required=False  # ✅ optional here
    # )

    groups = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=False,
        empty_label="Select Group",
        label="Assign Group"
    )

    class Meta:
        model = CustomUser
        fields = [
            'full_name', 
            'email', 
            # 'password', 
            'gender', 
            'contact' , 
            'groups'
        ]
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

        # if self.cleaned_data.get("password"):
        #     user.set_password(self.cleaned_data["password"])

        if commit:
            user.save()  # ensure user is in DB
            user.groups.set([])  # clears old groups safely
            if self.cleaned_data.get("groups"):
                user.groups.add(self.cleaned_data["groups"])
            print("Groups after save:", list(user.groups.all()))

        return user

'''
For pass reset when user login first time
'''
import re
from django import forms
from django.contrib.auth.forms import PasswordChangeForm

class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Extends Django's PasswordChangeForm to enforce:
      - exactly 8 characters,
      - at least 1 uppercase letter,
      - at least 1 digit,
      - at least 1 special character from the chosen set.
    """

    def clean_new_password2(self):
        new_password1 = self.cleaned_data.get("new_password1")
        new_password2 = self.cleaned_data.get("new_password2")

        if new_password1 and new_password2 and new_password1 != new_password2:
            raise forms.ValidationError("Passwords do not match.")

        # optionally, you can also validate password strength here

        return new_password2

    # def clean_new_password2(self):
    #     new_password2 = super().clean_new_password2()

    #     # Exactly 8 chars, at least one uppercase, one digit, one special char.
    #     pattern = re.compile(r'^(?=.{8}$)(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\<>?]).*$')

    #     if not pattern.match(new_password2):
    #         raise forms.ValidationError(
    #             "Password must be exactly 8 characters long and include at least 1 uppercase letter, "
    #             "1 number and 1 special character."
    #         )
    #     return new_password2

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
                'placeholder': 'Enter Department Name',
                'class': 'form-control'
            })
        }


class HrAssignedCompaniesForm(forms.ModelForm):
    hr = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(is_active=True, is_superuser=False).exclude(groups__name='local Admin'),
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
        fields = ["brand", "model_name", "engine_cc"]

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


class ConfigurationsForm(forms.ModelForm):
    as_of_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = Configurations
        fields = ['fuel_rate', 'as_of_date', 'bonus_constant_multiplier']

    def clean(self):
        cleaned_data = super().clean()
        # Basic validation to ensure fields are not negative
        fuel_rate = cleaned_data.get('fuel_rate')
        bonus_constant_multiplier = cleaned_data.get('bonus_constant_multiplier')

        if fuel_rate is not None and fuel_rate < 0:
            self.add_error('fuel_rate', 'Fuel rate cannot be negative.')
        if bonus_constant_multiplier is not None and bonus_constant_multiplier < 0:
            self.add_error('bonus_constant_multiplier', 'Bonus constant multiplier cannot be negative.')

        return cleaned_data