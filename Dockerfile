FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt
RUN pip install /app/app/sample_registry

ENV DB_FP=/app/db.sqlite3
ENV LOG_FP=/app

ENTRYPOINT [ "python" ]
CMD [ "app/app.py" ]