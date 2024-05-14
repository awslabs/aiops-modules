FROM rayproject/ray-ml

ADD . /aws/pytorch-ray

WORKDIR /aws/pytorch-ray

RUN pip install boto3

ENTRYPOINT ["python3", "/aws/pytorch-ray/pytorch_submit.py"]