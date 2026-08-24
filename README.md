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
- [Podman] (or another OCI builder) and Singularity to build the container image

## Installation

For single-user use, it is recommended to install the program using [`uv`][uv]:

```console
uv tool install /path/to/agent-container
agent-container --help
```

Alternatively, the program may be installed in a virtual environment using `uv`
or `pip`:

```console
# using uv
uv venv
uv pip install /path/to/agent-container
uv run agent-container --help
# or, using pip
python3 -m venv venv
venv/bin/pip install /path/to/agent-container
venv/bin/agent-container --help
```

Before agents can be started, you must build a container image (see
[Building the container image](#building-the-container-image)). The location of
this image can be specified via a global or a per-user configuration file (see
[Configuration](#configuration)) or via the `AGENT_CONTAINER` environment
variable.

## Example usage

To start a sandbox, run `agent-container` with one of the supported agents:

```console
cd /path/to/project
agent-container claude
```

Any arguments after the command are passed on to the agent or shell unchanged:

```console
agent-container claude --help
```

To include additional host folders in the sandbox, use the `--include` option
one or more times:

```console
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

```console
$ cd /path/to/my/workspace
$ agent-container new
workspace configured in '/path/to/my/workspace'
```

This workspace will be used for all sessions that are started in, or under,
`/path/to/my/workspace`.

Use `agent-container list` to see the configured workspaces:

```console
$ agent-container list
─ /path/to/my/workspace
    └ No paths included
```

## Configuration

Configuration files are located at `/etc/agent-container.toml` and
`~/.config/agent-container.toml`. If no configuration files exist, then
workspaces are permitted to be created anywhere.

The [configuration file](agent-container.toml) is a TOML file with the following
content:

```toml
# Regular expressions describing the paths of allowed workspaces. Matches are
# performed on resolved paths that always end with a `/`. The expression must
# match the entire path.
allowed_workspaces = [
    # "/maps/projects/\\w+(-AUDIT)?/people/\\w+/.*",
]

# Regular expressions describing paths that should never be allowed, even if
# they match a pattern in `allowed_workspaces`. As above, matches are performed
# on resolved paths that always end with a `/`, but unlike `allowed_workspaces`
# a pattern need only match the start of a path. For example,
# `/maps/projects/\w+-AUDIT/data/` excludes that folder and everything below it.
disallowed_workspaces = [
    # "/maps/projects/\\w+-AUDIT/data/",
]

# Default Singularity container containing the agents; may be overridden by
# setting the environment variable `AGENT_CONTAINER`. Must be an absolute path.
container = "/path/to/container.sif"

# List of absolute paths to folders that should always be mounted. These paths
# must be valid workspaces according to the allowed/disallowed lists above
includes = []
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

## Building the container image

Building is driven by the included [`Makefile`](Makefile) and uses Podman or
Docker to build an OCI image, which is then converted into a Singularity `.sif`
image.

```console
make sif
```

To build the container using Docker, instead run

```console
make sif MANAGER=docker
```

[podman]: https://podman.io/
[singularity]: https://sylabs.io/singularity/
[uv]: https://docs.astral.sh/uv/
