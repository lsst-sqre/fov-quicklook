FROM python:3.13-bookworm

ENV PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock /app/
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/ /app/
RUN uv sync --frozen --no-dev

ARG GIT_REVISION=unknown
ENV GIT_REVISION=${GIT_REVISION}
ENV PATH="/app/.venv/bin:$PATH"

COPY frontend/app/dist/ /app/frontend-assets/
COPY ci/review-app/entrypoint.sh /usr/local/bin/fov-quicklook-review-app-entrypoint
RUN chmod +x /usr/local/bin/fov-quicklook-review-app-entrypoint

EXPOSE 9500 9501 9502

ENTRYPOINT ["fov-quicklook-review-app-entrypoint"]
