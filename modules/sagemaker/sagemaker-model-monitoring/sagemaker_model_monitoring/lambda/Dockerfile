ARG PYTHON_VERSION=3.13
FROM public.ecr.aws/lambda/python:${PYTHON_VERSION}

# Install build dependencies for numpy and other packages
RUN dnf install -y gcc gcc-c++ make && \
    dnf clean all && \
    rm -rf /var/cache/dnf

# Upgrade pip to latest version
RUN pip install --no-cache-dir --upgrade pip

# Copy requirements and install dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt

# Copy function code
COPY *.py ${LAMBDA_TASK_ROOT}/

# Set the CMD to your handler
CMD ["baselining_handler.lambda_handler"]
