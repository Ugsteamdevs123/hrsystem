FROM python:3.12-slim
# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /code/app

COPY . /code/

RUN pip install -r /code/requirements.txt

COPY ./compose/django/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint

COPY ./compose/django/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start

# Move Celery worker, beat, and flower files inside /code/app/
COPY ./compose/django/celery/worker/start /start-celeryworker
COPY ./compose/django/celery/beat/start /start-celerybeat
COPY ./compose/django/celery/flower/start /start-flower

# Ensure all copied scripts are executable
RUN sed -i 's/\r$//g' /start-celeryworker && chmod +x /start-celeryworker
RUN sed -i 's/\r$//g' /start-celerybeat && chmod +x /start-celerybeat
RUN sed -i 's/\r$//g' /start-flower && chmod +x /start-flower

#export settings of project
ENV DJANGO_SETTINGS_MODULE=pyroll.settings

# port where the Django app runs  
EXPOSE 8044

ENTRYPOINT ["/entrypoint"]





# RUN pip install --upgrade pip && pip install -r requirements.txt


# COPY ./compose/django/entrypoint /entrypoint
# RUN sed -i 's/\r$//g' /entrypoint && chmod +x /entrypoint

# COPY ./compose/django/start /start
# RUN sed -i 's/\r$//g' /start && chmod +x /start

# # Move Celery worker, beat, and flower files inside /code/app/
# COPY ./compose/django/celery/worker/start /start-celeryworker
# COPY ./compose/django/celery/beat/start /start-celerybeat
# COPY ./compose/django/celery/flower/start /start-flower

# # Ensure all copied scripts are executable
# RUN sed -i 's/\r$//g' /start-celeryworker && chmod +x /start-celeryworker
# RUN sed -i 's/\r$//g' /start-celerybeat && chmod +x /start-celerybeat
# RUN sed -i 's/\r$//g' /start-flower && chmod +x /start-flower
# #export settings of project
# ENV DJANGO_SETTINGS_MODULE=bd_backend.settings
# # Set working dir for manage.py
# WORKDIR /code/app

# # port where the Django app runs  
# EXPOSE 7000

# ENTRYPOINT ["/entrypoint"]








