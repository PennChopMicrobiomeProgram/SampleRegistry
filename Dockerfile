FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt
RUN pip install /app/app/sample_registry

ENTRYPOINT [ "python" ]
CMD [ "app/app.py" ]