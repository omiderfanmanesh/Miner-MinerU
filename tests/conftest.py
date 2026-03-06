"""Shared pytest fixtures for TOC extraction tests."""
import pathlib
import pytest

DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
GOLDEN_DIR = pathlib.Path(__file__).parent / "golden"


def _find_md(subdir: str) -> pathlib.Path:
    folder = DATA_DIR / subdir
    matches = list(folder.glob("MinerU_markdown_*.md"))
    assert matches, f"No MinerU markdown found in {folder}"
    return matches[0]


@pytest.fixture(scope="session")
def notice_md_path() -> pathlib.Path:
    return _find_md(
        "Notice_of_competition_scholarship_accommodation_and_degree_award_a.y.2025.26_2026"
    )


@pytest.fixture(scope="session")
def disco_md_path() -> pathlib.Path:
    return _find_md("BANDO-DIRITTO-ALLO-STUDIO-25-26_ENG-compresso-alta")


@pytest.fixture(scope="session")
def bologna_md_path() -> pathlib.Path:
    return _find_md("bando-di-concorso-benefici-dsu-a-a-2025_26")


@pytest.fixture(scope="session")
def all_md_paths(notice_md_path, disco_md_path, bologna_md_path):
    return [notice_md_path, disco_md_path, bologna_md_path]
