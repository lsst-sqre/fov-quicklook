FROM python:3.13-bookworm

WORKDIR /app

COPY ./setup.py /app/setup.py

RUN \
  mkdir -p src && \
  pip install -U pip && \
  pip install -e .

COPY ./lib /app/lib
RUN \
  pip install ./lib/mineo-fits-decompress
  
COPY ./ /app/
