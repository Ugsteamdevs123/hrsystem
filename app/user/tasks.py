from dateutil.relativedelta import relativedelta
from celery import shared_task
from django.utils.timezone import now
import logging
from .models import Employee, EmployeeDraft, Configurations, FinancialImpactPerMonth, FinancialImpactPerMonthDraft

logger = logging.getLogger(__name__)

@shared_task
def task_day():
    try:
        configuration = Configurations.objects.first()
        # Calculate the date 6 calendar months ago
        six_months_ago = now().date() - relativedelta(months=6)

        # Find all non-intern employees who joined on or before that date
        employees = Employee.objects.filter(
            eligible_for_increment=False,
            is_intern=False,
            date_of_joining__lte=six_months_ago
        )

        for employee in employees:
            employee.eligible_for_increment = True
            employee.save(update_fields=['eligible_for_increment'])

            if configuration:
                join_date = employee.date_of_joining
                as_of_date = configuration.as_of_date

                if as_of_date < join_date:
                    total_days = 0
                else:
                    total_days = (as_of_date - join_date).days

                FinancialImpactPerMonth.objects.filter(employee_id=employee.id).update(
                    serving_period=total_days  # this is now in DAYS
                )

        # Do the same for EmployeeDraft
        employees_draft = EmployeeDraft.objects.filter(
            eligible_for_increment=False,
            is_intern=False,
            date_of_joining__lte=six_months_ago
        )

        for employee_draft in employees_draft:
            employee_draft.eligible_for_increment = True
            employee_draft.save(update_fields=['eligible_for_increment'])

            if configuration:
                join_date = employee_draft.date_of_joining
                as_of_date = configuration.as_of_date

                if as_of_date < join_date:
                    total_days = 0
                else:
                    total_days = (as_of_date - join_date).days

                FinancialImpactPerMonthDraft.objects.filter(employee_draft_id=employee_draft.id).update(
                    serving_period=total_days  # this is now in DAYS
                )

        logger.info("Task ran successfully and marked eligible employees")

        

        return "Completed task day"

    except Exception as e:
        logger.error(f"Error in task_day: {e}")
        return f"Error in task_day: {e}"
