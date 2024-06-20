FROM python:3.8-slim-buster
WORKDIR /flask_backend
COPY . /flask_backend
RUN pip install -r backend_requirements.txt
ENV FLASK_APP=run.py
CMD ["flask", "run", "-h", "0.0.0.0"]
