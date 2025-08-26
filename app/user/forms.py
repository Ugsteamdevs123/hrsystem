from django import forms
from .models import (
    Company , 
    CustomUser , 
    Gender,
    Section,
    DepartmentGroups,
    hr_assigned_companies,
    VehicleModel,
    VehicleInfo
)
from django.contrib.auth.models import Group





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




    # def save(self, commit=True):
    #     user = super().save(commit=False)

    #     # only update password if provided
    #     if self.cleaned_data.get("password"):
    #         user.set_password(self.cleaned_data["password"])

    #     if commit:
    #         user.save()

    #         # update group assignment
    #         user.groups.clear()  # remove old groups
    #         if self.cleaned_data.get("groups"):
    #             user.groups.add(self.cleaned_data["groups"])

    #     return user


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
    class Meta:
        model = VehicleModel
        fields = ["brand", "name", "year", "condition"]


class VehicleInfoForm(forms.ModelForm):
    class Meta:
        model = VehicleInfo
        fields = ["ownership_type", "color", "registration_number", "mileage_km"]


