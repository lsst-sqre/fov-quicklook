# for frontend
FROM node:23 as frontend

COPY ./frontend/ /frontend

# building javascripts can be done by the following commands, but it takes a long time.
# therefore, I recommend to build javascripts on your local machine and copy them to /frontend/app/dist

# RUN \
#   cd /frontend/lib/stellar-globe && npm install && npm run build && \
#   cd /frontend/lib/react-stellar-globe && npm install && npm run build && \
#   cd /frontend/app && npm install && npm run build

# for backend
FROM python:3.13-bookworm

WORKDIR /app

COPY ./backend/setup.py /app/setup.py

RUN \
  mkdir -p src && \
  pip install -U pip && \
  pip install -e .

COPY ./backend/lib /app/lib
RUN pip install ./lib/mineo-fits-decompress
  
COPY ./backend/ /app/

COPY --from=frontend /frontend/app/dist/ /app/frontend-assets
