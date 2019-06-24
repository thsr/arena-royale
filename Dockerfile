FROM python:3.6-alpine

WORKDIR app

COPY ./src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python", "./app.py" ]