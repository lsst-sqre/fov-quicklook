FROM public.ecr.aws/docker/library/node:24-bookworm AS node

FROM python:3.13-bookworm

ENV PYTHONUNBUFFERED=1 \
    SHELL=/usr/bin/fish \
    UV_SYSTEM_PYTHON=1 \
    PATH="/app/.venv/bin:$PATH"

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        fish \
        fzf \
        git \
        iproute2 \
        iputils-ping \
        jq \
        less \
        make \
        netcat-openbsd \
        postgresql-client \
        procps \
        ripgrep \
        tmux \
        vim \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -sf ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && ln -sf ../lib/node_modules/corepack/dist/corepack.js /usr/local/bin/corepack

COPY dev/microk8s-dev/config.fish /root/.config/fish/config.fish
COPY dev/microk8s-dev/fish_prompt.fish /root/.config/fish/functions/fish_prompt.fish
COPY dev/microk8s-dev/fish_right_prompt.fish /root/.config/fish/functions/fish_right_prompt.fish
COPY dev/microk8s-dev/tmux.conf /root/.tmux.conf
COPY dev/microk8s-dev/entrypoint.sh /usr/local/bin/fov-quicklook-dev-entrypoint

RUN mkdir -p /root/.local/share/fish /root/.cache/fish \
    && chmod +x /usr/local/bin/fov-quicklook-dev-entrypoint \
    && usermod -s /usr/bin/fish root

RUN curl -fsSL -o /usr/local/bin/kubectl "https://dl.k8s.io/release/v1.35.3/bin/linux/amd64/kubectl" \
    && chmod +x /usr/local/bin/kubectl

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock /app/
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/ /app/
RUN uv sync --frozen --no-dev

ARG GIT_REVISION=unknown
ENV GIT_REVISION=${GIT_REVISION}

WORKDIR /workspace/fov-quicklook

ENTRYPOINT ["fov-quicklook-dev-entrypoint"]
