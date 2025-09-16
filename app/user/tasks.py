from datetime import date
from dateutil.relativedelta import relativedelta
from celery import shared_task
from django.utils.timezone import now
import logging

logger = logging.getLogger(__name__)

@shared_task
def task_day():
    try:
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

        # Do the same for EmployeeDraft
        employees_draft = EmployeeDraft.objects.filter(
            eligible_for_increment=False,
            is_intern=False,
            date_of_joining__lte=six_months_ago
        )

        for employee_draft in employees_draft:
            employee_draft.eligible_for_increment = True
            employee_draft.save(update_fields=['eligible_for_increment'])

        logger.info("Task ran successfully and marked eligible employees")
        return "Completed task day"

    except Exception as e:
        logger.error(f"Error in task_day: {e}")
        return f"Error in task_day: {e}"
