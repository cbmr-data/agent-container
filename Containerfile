# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Mikkel Schubert
FROM debian:13.5

# Disable interactive front-end
ENV DEBIAN_FRONTEND=noninteractive

# Prevent cleanup of apt cache
RUN rm -fv /etc/apt/apt.conf.d/docker-clean

# Update base image
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update -y \
    && apt-get dist-upgrade -y \
    && apt-get autoremove -y --purge


# Basic dependencies and core tools
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update -y \
    && apt-get install -y \
      build-essential \
      ca-certificates \
      ccache \
      cmake \
      curl \
      fd-find \
      gdb \
      git \
      jq \
      locales \
      meson \
      nano \
      ninja-build \
      pkgconf \
      pre-commit \
      python3 \
      python3-pip \
      python3-venv \
      ripgrep \
      rsync \
      shellcheck \
      unzip \
      vim \
      wget \
      zip

# Install NodeJS 24 using the NodeSource repository
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && apt-get install -y \
        nodejs

# Install GitHub CLI from official repo
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    mkdir -p -m 755 /etc/apt/keyrings \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        | tee /etc/apt/keyrings/githubcli-archive-keyring.gpg \
        > /dev/null \
    && chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        | tee /etc/apt/sources.list.d/github-cli.list \
        > /dev/null \
    && apt-get update \
    && apt-get install -y gh

# Unused argument used to force installation of the latest versions
ARG BUILD_TAG=unknown
# Allow entry-point script to check if software installed in ~ should be updated
RUN touch /timestamp

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_UNMANAGED_INSTALL=/usr/local/bin bash

# Install pixi package manager
RUN curl -fsSL https://pixi.sh/install.sh | env PIXI_BIN_DIR=/usr/local/bin PIXI_NO_PATH_UPDATE=1 bash

# Install Claude Code
# Claude does not support global installs, so instead we use the
# installer capability of the installed executable
RUN curl -fsSL https://claude.ai/install.sh | bash \
    && cp -v ~/.local/bin/claude /usr/local/bin/claude-installer \
    && rm -rv ~/.local ~/.claude

# Install Codex CLI
RUN --mount=type=cache,target=/root/.cache,sharing=locked \
    --mount=type=cache,target=/root/.npm,sharing=locked \
    npm install -g @openai/codex

# Google Gemini CLI
RUN --mount=type=cache,target=/root/.cache,sharing=locked \
    --mount=type=cache,target=/root/.npm,sharing=locked \
    npm install -g @google/gemini-cli

# Github Copilot CLI
# The install script is used instead of NPM, since it doesn't download binaries
# for every arch. Running it as root installs copilot to /usr/local/bin
RUN curl -fsSL https://gh.io/copilot-install | bash

# Mistral Vibe
RUN uv venv /opt/mistral/ \
    && uv pip install \
        --no-cache \
        --directory /opt/mistral/ \
        mistral-vibe \
    && ln -s /opt/mistral/bin/vibe /opt/mistral/bin/vibe-acp /usr/local/bin/

# Locale matching Esrum HPC
RUN echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen \
    && locale-gen
ENV LC_ALL=en_US.utf8

# Configure simple prompt that to identify `agent-container` shells
# and ensure that locally installed tools (e.g. claude) are accessible
RUN mkdir -p /.singularity.d/env/ \
    && echo 'export PS1="(agent-container) \w $ "' > /.singularity.d/env/99-01-custom.sh \
    && echo 'export PATH=$HOME/.local/bin:$PATH' >> /.singularity.d/env/99-01-custom.sh \
    && echo 'export PATH=$HOME/.pixi/bin:$PATH' >> /.singularity.d/env/99-01-custom.sh

# Allow the user to set custom exports via ~/.profile
RUN echo 'test -e ~/.profile && . ~/.profile' > /.singularity.d/env/99-02.profile.sh

COPY --chmod=555 entrypoint.sh /bin/entrypoint.sh

ENTRYPOINT [ "/bin/entrypoint.sh" ]
