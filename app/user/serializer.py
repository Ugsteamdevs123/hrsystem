from rest_framework import serializers
from collections import OrderedDict
from .models import (
    IncrementDetailsSummary, 
    Formula,
    FieldFormula,
    DepartmentGroups, 
    Section, 
    Designation, 
    Location,
    EmployeeStatus,
    IncrementDetailsSummaryDraft,
)

class IncrementDetailsSummarySerializer(serializers.ModelSerializer):
    department = serializers.CharField(source="department_team.name", read_only=True)

    class Meta:
        model = IncrementDetailsSummary
        # exclude company (not needed in output)
        exclude = ['company', 'department_team']

    def to_representation(self, instance):
        """
        Customize output: 
        - replace underscores with spaces (except 'department')
        - enforce field order
        """
        rep = super().to_representation(instance)
        ordered = OrderedDict()

        # define the order explicitly
        field_order = [
            "id",
            "department",
            "total_employees",
            "eligible_for_increment",
            "current_salary",
            "effective_increment_rate_hod",
            "effective_fuel_percentage_hod",
            "salary_increment_impact_hod",
            "fuel_increment_impact_hod",
            "other_costs_in_p_and_l",
            "total_cost_on_p_and_l_per_month",
            "revised_department_salary",
            "staff_revised_cost",
            "approved",
            "is_draft"
        ]

        for field in field_order:
            if field in rep:
                # department should stay as is
                if field == "department":
                    ordered["department"] = rep[field]

                   
                else:
                    # replace _ with space for other fields
                    ordered[field.replace("_", " ")] = rep[field]

        return ordered


class IncrementDetailsSummaryDraftSerializer(serializers.ModelSerializer):
    department = serializers.CharField(source="department_team.name", read_only=True)

    class Meta:
        model = IncrementDetailsSummaryDraft
        # exclude company (not needed in output)
        exclude = ['company', 'department_team']

    def to_representation(self, instance):
        """
        Customize output: 
        - replace underscores with spaces (except 'department')
        - enforce field order
        """
        rep = super().to_representation(instance)
        ordered = OrderedDict()

        # define the order explicitly
        field_order = [
            "id",
            "department",
            "total_employees",
            "eligible_for_increment",
            "current_salary",
            "effective_increment_rate_hod",
            "effective_fuel_percentage_hod",
            "salary_increment_impact_hod",
            "fuel_increment_impact_hod",
            "other_costs_in_p_and_l",
            "total_cost_on_p_and_l_per_month",
            "revised_department_salary",
            "staff_revised_cost",
            "approved",
            "is_draft"
        ]

        for field in field_order:
            if field in rep:
                # department should stay as is
                if field == "department":
                    ordered["department"] = rep[field]
                    ordered["is_draft"] = True

                   
                else:
                    # replace _ with space for other fields
                    ordered[field.replace("_", " ")] = rep[field]

        return ordered
    

class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ['id', 'name']


class DepartmentGroupsSerializer(serializers.ModelSerializer):
    sections = SectionSerializer(many=True, read_only=True, source='section_set')

    class Meta:
        model = DepartmentGroups
        fields = ['id', 'name', 'sections']


class DesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Designation
        fields = ['id', 'title']

class DesignationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Designation
        fields = ['title', 'company']

    def validate_company(self, value):
        # Ensure company matches the department's company (passed in context)
        department_company_id = self.context.get('department_company_id')
        if department_company_id and value.id != department_company_id:
            raise serializers.ValidationError("Designation must belong to the same company as the department.")
        return value


class LocationsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Location
        fields = '__all__'


class EmployeeStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeStatus
        fields = '__all__'


class FormulaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Formula
        fields = ['formula_name', 'formula_expression', 'target_model', 'target_field']


class FieldFormulaSerializer(serializers.ModelSerializer):
    formula = FormulaSerializer(read_only=True)
    class Meta:
        model = FieldFormula
        fields = ['formula']