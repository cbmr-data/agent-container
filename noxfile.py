# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Mikkel Schubert
import nox

nox.options.default_venv_backend = "uv|virtualenv"
nox.options.sessions = [
    "style",
    "lints",
    "typing",
    "tests",
]


SOURCES = (
    "noxfile.py",
    "src",
    "tests",
)


@nox.session
def style(session: nox.Session) -> None:
    session.install("--group", "linting")

    session.run("ruff", "format", "--check", *SOURCES)


@nox.session
def lints(session: nox.Session) -> None:
    session.install("--group", "linting")

    session.run("ruff", "check", *SOURCES)


@nox.session
def typing(session: nox.Session) -> None:
    session.install("-e", ".", "--group", "typing")

    session.run("zuban", "check", *SOURCES)


@nox.session
def tests(session: nox.Session) -> None:
    # Install in development mode for coverage analysis
    session.install("-e", ".", "--group", "testing")

    session.run(
        "python",
        # Run tests in development mode (enables extra checks)
        "-X",
        "dev",
        # Treat warnings (deprecations, etc.) as errors
        "-Werror",
        "-m",
        "pytest",
        "--quiet",
        "tests",
        "--cov",
        "agent_container",
        "--cov",
        "tests",
        "--cov-report=xml",
        "--cov-report=term-missing",
        "--no-cov-on-fail",
    )
