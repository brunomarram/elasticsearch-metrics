FROM python:3.11.0a3-slim

ADD . /app

RUN useradd -u 10106 -r -s /bin/false monitor
RUN chmod 755 /app/bin/entrypoint.sh
RUN pip install requests

USER monitor

ENTRYPOINT [ "/app/bin/entrypoint.sh" ]
