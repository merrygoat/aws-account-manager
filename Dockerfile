FROM python:3.12

SHELL ["/bin/bash", "-c"]
ENV APP_DIR=/opt/aam

# Install git
RUN apt-get update && apt-get install git nginx

# Make a directory for the application and clone it
RUN mkdir ${APP_DIR}
WORKDIR ${APP_DIR}
RUN git clone https://github.com/merrygoat/amazon-account-manager.git .

# Make a new python venv, add it to the path and install required packages
ENV VIRTUAL_ENV=${APP_DIR}/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN python -m pip install --upgrade pip
RUN python -m pip install gunicorn
RUN python -m pip install -r requirements.txt

CMD gunicorn --bind 127.0.0.1:8080 aam:app