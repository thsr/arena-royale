FROM python:3.7-slim

WORKDIR app

COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# RUN pip install --upgrade pip
# RUN pip install opencv-python
RUN apt-get update && apt-get install -y libsm6 libxext6 libxrender-dev libglib2.0-0

CMD [ "python", "./app.py" ]