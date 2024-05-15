FROM python:3.12-slim

RUN apt-get clean && apt-get -y update
RUN apt-get -y install curl git

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt
RUN pip install metadatacli/

# Default values, can be overridden by config
ENV DB_FP=/data/db.sqlite3
ENV LOG_FP=/data/log
ENV URL=metadatachecker.tkg.research.chop.edu

ENTRYPOINT [ "python" ]
CMD [ "app/app.py" ]
