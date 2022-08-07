"""
Tasks for maintaining the project.

Execute 'invoke --list' for guidance on using Invoke
"""
import platform
import shutil
import webbrowser
from pathlib import Path

import pytest
from invoke import task, exceptions  # type: ignore


ROOT_DIR = Path(__file__).parent
BIN_DIR = ROOT_DIR.joinpath("bin")
SETUP_FILE = ROOT_DIR.joinpath("setup.py")
TEST_DIR = ROOT_DIR.joinpath("tests")
SOURCE_DIR = ROOT_DIR.joinpath("{{ cookiecutter.project_slug }}")
TOX_DIR = ROOT_DIR.joinpath(".tox")
COVERAGE_FILE = ROOT_DIR.joinpath(".coverage")
COVERAGE_DIR = ROOT_DIR.joinpath("htmlcov")
COVERAGE_REPORT = COVERAGE_DIR.joinpath("index.html")
DOCS_DIR = ROOT_DIR.joinpath("docs")
DOCS_SOURCE_DIR = DOCS_DIR.joinpath("source")
DOCS_BUILD_DIR = DOCS_DIR.joinpath("_build")
DOCS_INDEX = DOCS_BUILD_DIR.joinpath("index.html")
PYTHON_DIRS = [str(d) for d in [SOURCE_DIR, TEST_DIR]]


def _delete_file(file):
    try:
        file.unlink(missing_ok=True)
    except TypeError:
        # missing_ok argument added in 3.8
        try:
            file.unlink()
        except FileNotFoundError:
            pass


def _run(_c, command):
    return _c.run(command, pty=platform.system() != 'Windows')


@task(help={'check': "Checks if source is formatted without applying changes"})
def format(_c, check=False):
    """
    Format code
    """
    python_dirs_string = " ".join(PYTHON_DIRS)
    # Run black
    black_options = "--check" if check else ""
    _run(_c, f"black {black_options} {python_dirs_string}")
    # Run isort
    isort_options = "--check-only --diff" if check else ""
    _run(_c, f"isort {isort_options} {python_dirs_string}")


@task
def lint_flake8(_c):
    """
    Lint code with flake8
    """
    _run(_c, f"flake8 {' '.join(PYTHON_DIRS)}")


{% if cookiecutter.use_pylint == 'y' -%}
@task
def lint_pylint(_c):
    """
    Lint code with pylint
    """
    _run(_c, "pylint {}".format(" ".join(PYTHON_DIRS)))


{% endif %}
{% if cookiecutter.use_mypy == 'y' -%}
@task
def lint_mypy(_c):
    """
    Lint code with mypy
    """
    _run(_c, "mypy {}".format(" ".join(PYTHON_DIRS)))


{% endif %}
@task(lint_flake8{% if cookiecutter.use_pylint == 'y' -%}, lint_pylint{% endif %}{% if cookiecutter.use_mypy == 'y' -%}, lint_mypy{% endif %})
def lint(_c):
    """
    Run all linting
    """


@task(
    optional=["coverage"],
    help={
        "coverage": 'Add coverage, ="html" for html output or ="xml" for xml output',
        "junit": "Output a junit xml report",
    },
)
def test(_, coverage=None, junit=False):
    """Run tests"""
    pytest_args = ["-n", "auto"]

    if junit:
        junit_file = BIN_DIR / "report.xml"
        pytest_args.append(f"--junitxml={junit_file}")

    if coverage is not None:
        pytest_args.append(f"--cov={SOURCE_DIR}")

    if coverage == "html":
        pytest_args.append("--cov-report=html")
    elif coverage == "xml":
        xml_file = BIN_DIR / "coverage.xml"
        pytest_args.append(f"--cov-report=xml:{xml_file}")

    pytest_args.append(str(TEST_DIR))
    return_code = pytest.main(pytest_args)

    if coverage == "html":
        webbrowser.open(COVERAGE_REPORT.as_uri())

    if return_code:
        raise exceptions.Exit("Tests failed", code=return_code)


@task
def clean_docs(_c):
    """
    Clean up files from documentation builds
    """
    _run(_c, f"rm -fr {DOCS_BUILD_DIR}")
    _run(_c, f"rm -fr {DOCS_SOURCE_DIR}")


@task(pre=[clean_docs], help={"launch": "Launch documentation in the web browser"})
def docs(_c, launch=True):
    """
    Generate documentation
    """
    # Generate autodoc stub files
    _run(_c, f"sphinx-apidoc -e -P -o {DOCS_SOURCE_DIR} {SOURCE_DIR}")
    # Generate docs
    _run(_c, f"sphinx-build -b html {DOCS_DIR} {DOCS_BUILD_DIR}")
    if launch:
        webbrowser.open(DOCS_INDEX.as_uri())


@task
def clean_build(c):
    """
    Clean up files from package building
    """
    _run(c, "rm -fr build/")
    _run(c, "rm -fr dist/")
    _run(c, "rm -fr .eggs/")
    _run(c, "find . -name '*.egg-info' -exec rm -fr {} +")
    _run(c, "find . -name '*.egg' -exec rm -f {} +")


@task
def clean_python(c):
    """
    Clean up python file artifacts
    """
    _run(c, "find . -name '*.pyc' -exec rm -f {} +")
    _run(c, "find . -name '*.pyo' -exec rm -f {} +")
    _run(c, "find . -name '*~' -exec rm -f {} +")
    _run(c, "find . -name '__pycache__' -exec rm -fr {} +")


@task
def clean_tests(c):
    """
    Clean up files from testing
    """
    _delete_file(COVERAGE_FILE)
    shutil.rmtree(TOX_DIR, ignore_errors=True)
    shutil.rmtree(BIN_DIR, ignore_errors=True)
    shutil.rmtree(COVERAGE_DIR, ignore_errors=True)


@task(pre=[clean_build, clean_python, clean_tests, clean_docs])
def clean(c):
    """
    Runs all clean sub-tasks
    """
    pass


@task(clean)
def dist(c):
    """
    Build source and wheel packages
    """
    _run(c, "poetry build")


@task(pre=[clean, dist])
def release(c):
    """
    Make a release of the python package to pypi
    """
    _run(c, "poetry publish")
