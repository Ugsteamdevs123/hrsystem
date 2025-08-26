# In app/forms.py
from django import forms
from .models import Formula, FieldFormula, FieldReference


class FormulaForm(forms.ModelForm):

    class Meta:
        model = Formula
        fields = ['formula_name', 'formula_expression']
        widgets = {
            'formula_expression': forms.Textarea(attrs={'rows': 4, 'id': 'formula-expression'}),
        }

class FieldFormulaForm(forms.ModelForm):
    target_field = forms.ChoiceField(choices=[])

    class Meta:
        model = FieldFormula
        fields = ['target_model', 'target_field', 'formula', 'description']
        widgets = {
            'target_model': forms.Select(
                choices=[
                    ('', 'None'),
                    ('ProposedPackageDetails', 'Proposed Package Details'),
                    ('FinancialImpactPerMonth', 'Financial Impact Per Month'),
                    ('IncrementDetailsSummary', 'Increment Details Summary'),
                ],
                attrs={'required': 'true'}  # HTML required attribute for UI
            ),
            'target_field': forms.Select(
                attrs={'required': 'true'}  # HTML required attribute
            ),
            'formula': forms.Select(
                attrs={'required': 'true'}  # HTML required attribute
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If editing or form submitted with target_model selected
        model_name = None
        if 'target_model' in self.data:
            model_name = self.data.get('target_model')
        elif self.instance.pk:
            model_name = self.instance.target_model

        if model_name:
            from django.apps import apps
            try:
                model = apps.get_model("user", model_name)
                fields = [f.name for f in model._meta.get_fields() if not f.is_relation]
                self.fields['target_field'].choices = [(f, f) for f in fields]
            except LookupError:
                self.fields['target_field'].choices = []
            







from .utils import iter_allowed_models, get_model_by_name, list_fields
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