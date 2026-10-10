FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/home/appuser
WORKDIR /app

COPY module_6/src/worker/requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --create-home --no-log-init appuser \
    && chown 1000:1000 /app

COPY --chown=1000:1000 module_6/__init__.py /app/module_6/__init__.py
COPY --chown=1000:1000 module_6/src /app/module_6/src
COPY --chown=1000:1000 module_2/*.py /app/module_2/

USER 1000
CMD ["python", "-m", "module_6.src.worker.consumer"]
