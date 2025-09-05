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

#export settings of project
ENV DJANGO_SETTINGS_MODULE=pyroll.settings

# port where the Django app runs  
EXPOSE 8044

ENTRYPOINT ["/entrypoint"]







