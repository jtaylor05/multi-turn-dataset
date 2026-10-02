FROM python:3.11-slim

WORKDIR /app

COPY ./main.py /app/main.py
COPY ./src /app/src
COPY ./requirements.txt /app/requirements.txt

# Install the openai library
RUN pip install --no-cache-dir -r /app/requirements.txt

VOLUME ["/app/data"]

# Default command
CMD ["/bin/bash"]