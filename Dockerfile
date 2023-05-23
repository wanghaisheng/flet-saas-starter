FROM python:3-alpine

WORKDIR /app

ENV FLET_SERVER_PORT "8080"

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "./main.py"]
