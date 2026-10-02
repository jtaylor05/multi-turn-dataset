FROM python:3.11-slim

WORKDIR /app

COPY initial_generation/bin /app/bin
COPY initial_generation/requirements.txt /app/requirements.txt
COPY prompts /app/prompts

RUN chmod +x /app/bin/*
RUN pip install --no-cache-dir -r /app/requirements.txt

ENV PATH="/app/bin:${PATH}"
ENV PROMPTS_DIR="/app/prompts"

VOLUME ["/app/data"]

CMD ["/bin/bash"]