FROM python:3.12-slim

ARG NOTEBOOKLM_VERSION=0.8.3

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NOTEBOOKLM_HOME=/data \
    NOTEBOOKLM_PROFILE=server \
    NOTEBOOKLM_MCP_ALLOW_EXTERNAL_BIND=1

RUN pip install --no-cache-dir "notebooklm-py[mcp,headless]==${NOTEBOOKLM_VERSION}"

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod 0755 /app/entrypoint.sh

EXPOSE 8080
ENTRYPOINT ["/app/entrypoint.sh"]
