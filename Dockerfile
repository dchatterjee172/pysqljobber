FROM python:3.9-slim as builder
RUN apt-get update \
    && apt-get install -y gcc
RUN pip install poetry==1.1.15
RUN python -m venv /venv
WORKDIR /code
COPY poetry.lock pyproject.toml /code/
RUN . /venv/bin/activate \
    && poetry install --no-dev --no-interaction
COPY . /code/
RUN . /venv/bin/activate \
    && poetry build

FROM python:3.9-slim as final
COPY --from=builder /venv /venv
COPY --from=builder /code/dist .
RUN . /venv/bin/activate \
    && pip install *.whl
RUN chmod +x /venv/bin/pysqljobber
ENTRYPOINT ["/venv/bin/pysqljobber"]
