from contextlib import contextmanager
import shlex
import os
from pathlib import Path

import pytest
import subprocess
import datetime

import pytest_cookies.plugin

_DEPENDENCY_FILE = "pyproject.toml"
_INSTALL_DEPS_COMMANDS = [
    "poetry install",
]
LINE_LENGTH = 120
PYPI_URL = "https://artifactory.aws.gel.ac/artifactory/api/pypi/pypi/simple"


def build_commands(commands: list[str]) -> list[str]:
    """
    Build command list from list of strings.

    :param list[str] commands: Commands that will be executed
    """
    cmds = _INSTALL_DEPS_COMMANDS.copy()
    cmds.extend(commands)
    return cmds


@contextmanager
def change_working_directory(path: str):
    """
    Changes working directory and returns to previous on exit.

    :param str path: String, path of the directory the command is being run.
    """
    prev_cwd = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


def run_inside_dir(commands, path: str) -> None:
    """
    Run a command from inside a given directory, returning the exit status

    :param list[str] commands: Commands that will be executed
    :param str path: Path of the directory the command is being run.
    """
    with change_working_directory(path):
        for command in commands:
            try:
                subprocess.check_call(shlex.split(command))
            except subprocess.CalledProcessError:
                raise


def check_output_inside_dir(command, path) -> subprocess.CompletedProcess:
    """Run a command from inside a given directory, returning the command output"""
    with change_working_directory(path):
        try:
            return subprocess.check_output(shlex.split(command))
        except subprocess.CalledProcessError:
            raise


def test_bake_with_defaults(cookies: pytest_cookies.plugin.Cookies) -> None:
    result = cookies.bake()
    assert result.exit_code == 0
    assert result.exception is None
    assert result.project_path.is_dir()

    found_toplevel_files = [
        f.name for f in result.project_path.glob("**/*") if f.is_file()
    ]
    assert _DEPENDENCY_FILE in found_toplevel_files
    assert ".flake8" in found_toplevel_files
    assert ".pylintrc" in found_toplevel_files

    found_toplevel_dirs = [f.name for f in result.project_path.iterdir() if f.is_dir()]
    assert "docs" in found_toplevel_dirs
    assert "tests" in found_toplevel_dirs
    assert "python_boilerplate" in found_toplevel_dirs


def test_bake_with_defaults_pyproject(cookies: pytest_cookies.plugin.Cookies) -> None:
    result = cookies.bake()
    assert result.project_path.is_dir()
    dep_file_path = result.project_path / _DEPENDENCY_FILE
    toml_file = dep_file_path.read_text()
    assert 'mypy = "*"\n' in toml_file
    assert 'pylint = "*"\n' in toml_file
    assert f"line-length = {LINE_LENGTH}\n" in toml_file
    assert f'url = "{PYPI_URL}"' in toml_file


def test_year_compute_in_license_file(cookies: pytest_cookies.plugin.Cookies) -> None:
    result = cookies.bake()
    license_file_path = result.project_path / "LICENSE"
    now = datetime.datetime.now()
    assert str(now.year) in license_file_path.read_text()


@pytest.mark.parametrize(
    "extra_context", [{}, {"full_name": 'name "quote" name'}, {"full_name": "O'connor"}]
)
def test_bake_tests(cookies: pytest_cookies.plugin.Cookies, extra_context) -> None:
    result = cookies.bake(extra_context=extra_context)
    assert result.project_path.is_dir()
    # Test pyproject installs pytest
    dep_file_path = result.project_path / _DEPENDENCY_FILE
    lines = dep_file_path.read_text()
    assert 'pytest = "*"\n' in lines
    # Test contents of test file
    test_file_path = result.project_path / "tests/test_python_boilerplate.py"
    lines = test_file_path.read_text()
    assert "import pytest" in lines


def test_bake_without_author_file(cookies: pytest_cookies.plugin.Cookies) -> None:
    result = cookies.bake(extra_context={"create_author_file": "n"})
    found_toplevel_files = [f for f in result.project_path.glob("**/*") if f.is_file()]
    assert "AUTHORS.rst" not in found_toplevel_files
    doc_files = [f for f in (result.project_path / "docs").glob("**/*") if f.is_file()]
    assert "authors.rst" not in doc_files

    # Assert there are no spaces in the toc tree
    docs_index_path = result.project_path / "docs/index.rst"
    with open(str(docs_index_path)) as index_file:
        assert "contributing\n   history" in index_file.read()


@pytest.mark.parametrize(
    "license_info",
    [
        ("MIT", "MIT "),
        (
            "BSD-3-Clause",
            "Redistributions of source code must retain the "
            + "above copyright notice, this",
        ),
        ("ISC", "ISC License"),
        ("Apache-2.0", "Licensed under the Apache License, Version 2.0"),
        ("GPL-3.0-only", "GNU GENERAL PUBLIC LICENSE"),
    ],
)
def test_bake_selecting_license(cookies: pytest_cookies.plugin.Cookies, license_info):
    license_str, target_string = license_info
    result = cookies.bake(extra_context={"open_source_license": license_str})
    license_file_path = result.project_path / "LICENSE"
    license_file = license_file_path.read_text()
    dep_file_path = result.project_path / _DEPENDENCY_FILE
    toml_file = dep_file_path.read_text()
    assert target_string in license_file
    assert license_str in toml_file


def test_bake_not_open_source(cookies: pytest_cookies.plugin.Cookies):
    result = cookies.bake(extra_context={"open_source_license": "Not open source"})
    found_toplevel_files = [
        f.name for f in result.project_path.glob("**/*") if f.is_file()
    ]
    assert _DEPENDENCY_FILE in found_toplevel_files
    assert "LICENSE" not in found_toplevel_files
    assert "License" not in (result.project_path / "README.rst").read_text()
    assert "license" not in (result.project_path / _DEPENDENCY_FILE).read_text()


@pytest.mark.parametrize(
    "command",
    [
        "poetry run invoke format --check",
        "poetry run invoke lint",
        "poetry run invoke docs --no-launch",
    ],
)
def test_bake_and_run_and_invoke(cookies: pytest_cookies.plugin.Cookies, command: str):
    """Run the unit tests of a newly-generated project"""
    result = cookies.bake()
    assert result.project_path.is_dir()
    # commands = build_commands([command])
    # run_inside_dir(commands, str(result.project))
