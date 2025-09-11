# from __future__ import absolute_import, unicode_literals
# import os
# from celery import Celery
# # from dotenv import load_dotenv

# from django.conf import settings

# # load_dotenv()

# # Set the default Django settings module for the 'celery' program.
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pyroll.settings')


# REDIS_URL = settings.REDIS_URL

# app = Celery('pyroll',
#             broker=f'{REDIS_URL}/1',
#             backend = f'{REDIS_URL}/1',
#             )
# app.conf.timezone = 'UTC'
# app.conf.broker_connection_retry_on_startup = True
# # Configure Celery using settings from Django settings.py.
# # app.config_from_object(settings, namespace='CELERY')
# # app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'


# # Load tasks from all registered Django app configs.
# app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
# app.autodiscover_tasks()

import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

app = Celery('myproject')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()