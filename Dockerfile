FROM tensorflow/tensorflow:2.18.0

ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt --ignore-installed

COPY . .

EXPOSE 80

CMD ["gunicorn", "--bind", "0.0.0.0:80", "app:app"]