# agent-container -- run AI agents with limited scope

`agent-container` is a sandbox meant for simplifying the use of AI coding agents
on systems where users have access to sensitive data.

Agents are run in a [Singularity] (Apptainer) container that only has access to
your current working directory, to any folders you explicitly include, and to a
persistent home folder (separate from your normal home folder).

The sandbox includes `claude`, `codex`, `gemini`, `copilot` and `vibe`, together
with a set of common development tools (`git`, `gh`, `jq`, `ripgrep`, `fd`,
Node.js, `uv`, `pixi`, Python, and a C/C++ toolchain, on top of a Debian base
image.

## Limitations

- Folder allow/disallow lists are based on regular expressions. Therefore, if
  you allow `/some/path` and disallow `/some/path/data`, then the user will be
  able to start a sandbox in `/some/path` that includes access to
  `/some/path/data`.

## Requirements

- Python 3.12 or newer
- [`uv`][uv] for installing and managing the project
- [Singularity] / Apptainer available on `PATH` to run agents
- [Podman] or [Docker] to build the container image

## Installation and upgrading

Download the latest version `agent-container`:

```bash
git clone https://github.com/cbmr-data/agent-container.git
```

For single-user use, it is recommended to install the program using [`uv`][uv]:

```bash
uv tool install /path/to/agent-container
agent-container --help
```

Alternatively, the program may be installed in a virtual environment using `uv`
or `pip`:

```bash
# using uv
uv venv
uv pip install /path/to/agent-container
uv run agent-container --help
# or, using pip
python3 -m venv venv
./venv/bin/pip install /path/to/agent-container
./venv/bin/agent-container --help
```

### Building the container image

Before agents can be started, you must build a Singularity container image. This
may be done using the included [`Makefile`](Makefile), which uses Podman or
Docker to build an OCI image, and then converts it to a Singularity `.sif`
image.

```bash
cd /path/to/agent-container
make sif                 # build using podman,
make sif MANAGER=podman  # or build using podman (explicitly),
make sif MANAGER=docker  # or build using docker
```

Images are time-stamped using the current date, so that an updated image can be
generated simply by running `make` again. Additionally, a symlink named
`agent-container-latest.sif` is automatically created that points to the latest
`.sif` file.

### Minimal configuration

For `agent-container` to locate the `.sif` file, you must either create a
`agent-container.toml` configuration file as described below or set the
`AGENT_CONTAINER` environment variable so that the script can locate the `.sif`
file:

```bash
export AGENT_CONTAINER=/path/to/agent-container/build/agent-container-latest.sif
```

You can save this command in your `~/.bashrc` (or other such) file, but note
that you will need to remove the command if you subsequently want to set the
path using a `agent-container.toml` file, since the environment variable is
given priority.

For example, while in the

### Upgrading

To upgrade `agent-container`, download the latest version and repeat the
`install` command you used:

```bash
cd /path/to/agent-container # 1. download latest version
git pull
uv tool install .
```

For installations in a virtual environment, repeat the `install` command used
above, e.g:

```bash
cd /path/to/uv-venv/
uv pip install /path/to/agent-container
```

or

```bash
cd /path/to/pip-venv/
./venv/bin/pip install /path/to/agent-container
```

Remember to also (re)build the container image as described above.

## Example usage

To start a sandbox, run `agent-container` with one of the supported agents:

```bash
cd /path/to/project
agent-container claude
```

Any arguments after the command are passed on to the agent or shell unchanged:

```bash
agent-container claude --help
```

To include additional host folders in the sandbox, use the `--include` option
one or more times:

```bash
agent-container --include /path/to/other/project claude
```

By default, `agent-container` is allowed to create a workspace at any location,
but this behavior may be [configured](#configuration), to reduce the chance of
data exfiltration.

## Workspaces

Each agent run is given a _home_ directory that persists between invocations, so
agent configuration, credentials, and history are retained. By default, all
allowed directories share a single `global` home.

Running `agent-container new` in a directory instead creates a dedicated
_workspace_ for it, giving that directory, and everything beneath it, its own
isolated home.

```bash
$ cd /path/to/my/workspace
$ agent-container new
workspace configured in '/path/to/my/workspace'
```

This workspace will be used for all sessions that are started in, or under,
`/path/to/my/workspace`.

Use `agent-container list` to see the configured workspaces:

```bash
$ agent-container list
─ /path/to/my/workspace
    └ No paths included
```

## Configuration files

Configuration files are located at `/etc/agent-container.toml` and
`~/.config/agent-container.toml`. If no configuration files exist, then
workspaces are permitted to be created anywhere.

The [configuration file](agent-container.toml) is a TOML file with the following
content:

```toml
# Regular expressions describing the paths of allowed workspaces. Matches are
# performed on resolved paths that always end with a `/`. The expression must
# match the entire path. If `allowed_workspaces` is not set, then all paths that
# are not explicitly disallowed are permitted.
allowed_workspaces = [
  # "/maps/projects/\w+(-AUDIT)?/people/\w+/.*",
]

# Regular expressions describing paths that should never be allowed, even if
# they match a pattern in `allowed_workspaces`. As above, matches are performed
# on resolved paths that always end with a `/`, but unlike `allowed_workspaces`
# a pattern need only match the start of a path. For example,
# `/maps/projects/\w+-AUDIT/data/` excludes that folder and everything below it.
disallowed_workspaces = [
  # "/maps/projects/\w+-AUDIT/data/",
]

# Default singularity container containing agents; may be overridden by setting
# the environment variable `AGENT_CONTAINER`
container = "/path/to/container.sif"

# List of absolute paths to folders that should always be mounted. These paths
# must be valid workspaces according to the allowed/disallowed lists above.
# Includes may end with `:ro` to indicate read-only paths (e.g. for datasets) or
# `:rw` to indicate writable paths (e.g. tmp/scratch folders). The `--read-only`
# option does not affect includes marked in this manner. includes = []
```

If both a global and a user configuration file is specified, then the two are
merged as follows:

- The global `allowed_workspaces` setting takes precedence, if set.
- The global and the user `disallowed_workspaces` settings are combined.
- The user `container` value takes precedence, if set.
- The global and the user `includes` settings are combined.

## Environment variables

| Variable                  | Description                                                                                                                     |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `AGENT_CONTAINER`         | Absolute path to Singularity image, overriding `container` in the configuration file.                                           |
| `AGENT_CONTAINER_STORAGE` | Absolute path to the directory used for workspace metadata and per-workspace homes (default: `~/.local/share/agent-container`). |

## Customizing the container

It is recommended to use [`uv`][uv] and [`pixi`][pixi] to install dependencies
in the container, as this greatly simplifies the process:

```bash
# 1. installing python software using `uv tool`:
$ uv tool install mdformat --with mdformat-gfm
$ mdformat --version
mdformat 1.0.0 (mdformat-gfm 1.0.0)

# 2. install conda packages using `pixi global`:
$ pixi global install ncdu
$ ncdu --version
ncdu 1.22
```

By design, the agent-container does not inherit environment variables from the
environment in which it was executed. Instead, you can set environment variables
in the environment using the per-workspace `~/.profile` file:

```bash
$ agent-container shell
$ nano ~/.profile
```

[docker]: https://www.docker.com/
[pixi]: https://pixi.prefix.dev
[podman]: https://podman.io/
[singularity]: https://sylabs.io/singularity/
[uv]: https://docs.astral.sh/uv/
