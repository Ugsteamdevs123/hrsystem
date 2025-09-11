from django.utils.timezone import now
from celery import shared_task
from .models import Location, Employee, EmployeeDraft
import logging
from dateutil.relativedelta import relativedelta


logger = logging.getLogger(__name__)


@shared_task
def task_seconds():
    try:
        print("Doing work")
        six_months_ago = now().date() - relativedelta(months=6)

        employees = Employee.objects.filter(
            eligible_for_increment=False,
            auto_mark_eligibility=True,
            is_intern=False,
            date_of_joining__lte=six_months_ago  # Joined on or before 6 months ago
        )

        for employee in employees:
            employee.eligible_for_increment = True
            employee.save(update_fields=['eligible_for_increment'])
        
        employees_draft = EmployeeDraft.objects.filter(
            eligible_for_increment=False,
            auto_mark_eligibility=True,
            is_intern=False,
            date_of_joining__lte=six_months_ago  # Joined on or before 6 months ago
        )

        for employee_draft in employees_draft:
            employee_draft.eligible_for_increment = True
            employee_draft.save(update_fields=['eligible_for_increment'])

        print("Work done")
        logger.info("Task running every 30 seconds")
        return "Completed 30-second task"
    except Exception as e:
        return f"Error in 30-second task: {e}"

# @shared_task
# def task_days():
#     logger.info("Task running every 2 days")
#     return "Completed 2-day task"

# @shared_task
# def task_monthly():
#     logger.info("Task running on the 1st of every month")
#     return "Completed monthly task"