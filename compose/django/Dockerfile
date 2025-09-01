FROM python:3.12-slim
# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1





WORKDIR /code/app

COPY . /code/




RUN pip install -r requirements.txt

COPY ./compose/django/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint

COPY ./compose/django/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start




# # Move Celery worker, beat, and flower files inside /code/app/
# COPY ./compose/django/celery/worker/start /start-celeryworker
# COPY ./compose/django/celery/beat/start /start-celerybeat

# # Ensure all copied scripts are executable
# RUN sed -i 's/\r$//g' /start-celeryworker && chmod +x /start-celeryworker
# RUN sed -i 's/\r$//g' /start-celerybeat && chmod +x /start-celerybeat

#export settings of project
ENV DJANGO_SETTINGS_MODULE=pyroll.settings


# port where the Django app runs  
EXPOSE 8000

ENTRYPOINT ["/entrypoint"]