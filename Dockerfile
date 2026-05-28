FROM python:3.12-slim

LABEL maintainer="nesquena"
LABEL description="Hermes Web UI — browser interface for Hermes Agent"

# Install system packages
ENV DEBIAN_FRONTEND=noninteractive

# Make use of apt-cacher-ng if available
RUN if [ "A${BUILD_APT_PROXY:-}" != "A" ]; then \
        echo "Using APT proxy: ${BUILD_APT_PROXY}"; \
        printf 'Acquire::http::Proxy "%s";\n' "$BUILD_APT_PROXY" > /etc/apt/apt.conf.d/01proxy; \
    fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates wget gnupg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN apt-get update -y --fix-missing --no-install-recommends \
    && apt-get install -y --no-install-recommends \
    apt-utils \
    locales \
    ca-certificates \
    curl \
    rsync \
    openssh-client \
    git \
    xz-utils \
    && apt-get upgrade -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# UTF-8
RUN localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8
ENV LANG=en_US.utf8
ENV LC_ALL=C

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

WORKDIR /apptoo

# Create the unprivileged runtime user. The entrypoint starts as root only for
# UID/GID alignment and filesystem preparation, then execs the server as this user.
RUN groupadd -g 1024 hermeswebui \
    && useradd -u 1024 -d /home/hermeswebui -g hermeswebui -G users -s /bin/bash -m hermeswebui \
    && mkdir -p /app /uv_cache /workspace \
    && chown -R hermeswebui:hermeswebui /home/hermeswebui /app /uv_cache /workspace \
    && chmod 0755 /home/hermeswebui \
    && chmod 1777 /app /uv_cache /workspace

COPY --chmod=555 docker_init.bash /hermeswebui_init.bash

RUN touch /.within_container

# Remove APT proxy configuration and clean up APT downloaded files
RUN rm -rf /var/lib/apt/lists/* /etc/apt/apt.conf.d/01proxy \
    && apt-get clean

USER root

# Pre-install uv system-wide so the container doesn't need internet access at runtime.
# Installing as root places uv in /usr/local/bin, available to all users.
# The init script will skip the download when uv is already on PATH.
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh

COPY --chown=root:root . /apptoo

# Bake the git version tag into the image so the settings badge works even
# when .git is not present (it is excluded by .dockerignore).
# CI passes: --build-arg HERMES_VERSION=$(git describe --tags --always)
# Local builds that omit the arg get "unknown" as the fallback.
ARG HERMES_VERSION=unknown
RUN echo "__version__ = '${HERMES_VERSION}'" > /apptoo/api/_version.py

# ── Bake hermes-agent into the image ──────────────────────────────────────────
# Clone the official hermes-agent source to /opt/hermes so that all modules
# (cron, agent, gateway, etc.) are available at runtime without a mounted volume.
# docker_init.bash already knows to look here as its second-priority agent path.
#
# At runtime, mounting a local checkout at
#   /home/hermeswebui/.hermes/hermes-agent   (first-priority path)
# will take precedence — useful for developers who want to test local changes.
#
# Build args let CI pin or override the source:
#   --build-arg HERMES_AGENT_REPO=https://github.com/NousResearch/hermes-agent.git
#   --build-arg HERMES_AGENT_REF=main
ARG HERMES_AGENT_REPO=https://github.com/NousResearch/hermes-agent.git
ARG HERMES_AGENT_REF=main
# Clone to /opt/hermes-agent — this exact path is in config.py's discovery list
RUN git clone --depth=1 --branch "${HERMES_AGENT_REF}" "${HERMES_AGENT_REPO}" /opt/hermes-agent \
    && chown -R hermeswebui:hermeswebui /opt/hermes-agent

# Pre-warm the uv dependency cache with ALL Python packages (webui + agent).
# docker_init.bash creates the real venv at first startup, but with a warm cache
# all packages are installed from disk rather than downloaded from PyPI, so the
# first container boot completes in seconds instead of minutes.
# The throwaway venv is discarded; only /uv_cache is kept in the final image.
RUN UV_CACHE_DIR=/uv_cache uv venv /tmp/prebuild-venv \
    && UV_CACHE_DIR=/uv_cache VIRTUAL_ENV=/tmp/prebuild-venv \
       uv pip install -r /apptoo/requirements.txt \
           --trusted-host pypi.org --trusted-host files.pythonhosted.org \
    && UV_CACHE_DIR=/uv_cache VIRTUAL_ENV=/tmp/prebuild-venv \
       uv pip install /opt/hermes-agent[all] \
           --trusted-host pypi.org --trusted-host files.pythonhosted.org \
    && rm -rf /tmp/prebuild-venv \
    && chmod -R 777 /uv_cache

# Default to binding all interfaces (required for container networking)
ENV HERMES_WEBUI_HOST=0.0.0.0
ENV HERMES_WEBUI_PORT=8787

EXPOSE 8787

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8787/health || exit 1

# docker_init.bash performs root-only bind-mount setup, then drops to hermeswebui
# before starting the WebUI server. The production image does not ship sudo.
USER root
CMD ["/hermeswebui_init.bash"]

