# for frontend
# FROM node:24 AS frontend
FROM public.ecr.aws/docker/library/node:24 AS frontend

COPY ./frontend/ /frontend

# building javascripts can be done by the following commands, but it takes a long time.
# therefore, I recommend to build javascripts on your local machine and copy them to /frontend/app/dist

RUN \
  cd /frontend/lib/stellar-globe/stellar-globe && npm install && npm run build && \
  cd /frontend/lib/stellar-globe/react-stellar-globe && npm install && npm run build && \
  cd /frontend/app && npm install && npm run build

# for backend
FROM python:3.13-bookworm

# Install uv via pip (alternative to COPY --from=ghcr.io/astral-sh/uv:latest)
RUN pip install uv

WORKDIR /app

# Copy dependency files first for better caching
COPY ./backend/pyproject.toml ./backend/uv.lock /app/

# Install dependencies (without dev dependencies)
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY ./backend/ /app/

# Install the project itself
RUN uv sync --frozen --no-dev

# Add virtual environment to PATH so python, alembic, etc. are available
ENV PATH="/app/.venv/bin:$PATH"

COPY --from=frontend /frontend/app/dist/ /app/frontend-assets
