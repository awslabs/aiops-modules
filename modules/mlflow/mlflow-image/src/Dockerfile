FROM python:3.10.12

RUN pip install \
    mlflow==2.10.2 \
    pymysql==1.1.0 \
    boto3==1.34.45 && \
    mkdir /mlflow/

EXPOSE 5000

CMD if [ -n "$HOST" ]; then \
        mlflow server \
        --host 0.0.0.0 \
        --port 5000 \
        --default-artifact-root ${BUCKET} \
        --backend-store-uri mysql+pymysql://${USERNAME}:${PASSWORD}@${HOST}:${PORT}/${DATABASE}; \
    else \
        mlflow server \
        --host 0.0.0.0 \
        --port 5000 \
        --default-artifact-root ${BUCKET}; \
    fi
