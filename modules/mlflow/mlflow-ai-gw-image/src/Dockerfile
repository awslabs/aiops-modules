FROM public.ecr.aws/docker/library/python:3.10.15

RUN pip install \
    'mlflow[gateway]' \
    mlflow==2.17.0 && \
    mkdir /mlflow/

EXPOSE 7000

COPY config.yaml ./mlflow/config.yaml

CMD mlflow gateway start \
    --host 0.0.0.0 \
    --port 7000 \
    --config-path ./mlflow/config.yaml;
