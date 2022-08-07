"""Development tasks for the cookiecutter template project"""
import shutil
import webbrowser
from pathlib import Path
import platform
from invoke import task

ROOT_DIR = Path(__file__).parent
DOCS_DIR = ROOT_DIR.joinpath("docs")
DOCS_BUILD_DIR = DOCS_DIR.joinpath("_build")
DOCS_INDEX = DOCS_BUILD_DIR.joinpath("index.html")
TOX_DIR = ROOT_DIR.joinpath(".tox")
TEST_CACHE_DIR = ROOT_DIR.joinpath(".pytest_cache")


def _run(c, command):
    return c.run(command, pty=platform.system() != "Windows")


@task
def test(c):
    """
    Run tests
    """
    _run(c, "pytest")


@task
def docs(c):
    """
    Generate documentation
    """
    _run(c, "sphinx-build -b html {} {}".format(DOCS_DIR, DOCS_BUILD_DIR))
    webbrowser.open(DOCS_INDEX.absolute().as_uri())


@task
def clean_docs(_):
    """
    Clean up files from documentation builds
    """
    shutil.rmtree(DOCS_BUILD_DIR, ignore_errors=True)


@task
def clean_tests(_):
    """Clean up files from testing"""
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)


@task
def clean_tox(_):
    """Clean up files from testing"""
    shutil.rmtree(TOX_DIR, ignore_errors=True)


@task(pre=[clean_docs, clean_tests, clean_tox])
def clean(_):
    """Runs all clean sub-tasks"""
