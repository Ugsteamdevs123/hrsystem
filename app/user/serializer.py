from rest_framework import serializers
from collections import OrderedDict
from .models import IncrementDetailsSummary

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
