"""
Dashboard smoke tests.

AppTest runs a Streamlit script in a headless test harness and reports
any exception raised during the run, without needing a browser. These
tests only exercise the default, no-interaction load of each page (the
state a fresh visitor sees); the actual look of the pages, and their
behaviour after clicking buttons and moving sliders, was checked by hand
against screenshots during development, not by these tests.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from streamlit.testing.v1 import AppTest

PAGES = [
    "app/views/overview.py",
    "app/views/control.py",
    "app/views/instrumentation.py",
    "app/views/experiments.py",
    "app/views/faults.py",
    "app/views/analysis.py",
]


@pytest.mark.parametrize("page_path", PAGES)
def test_page_loads_without_exception(page_path):
    at = AppTest.from_file(str(PROJECT_ROOT / page_path))
    at.run(timeout=30)
    assert not at.exception, f"{page_path} raised: {at.exception}"


def test_overview_runs_a_simulation_end_to_end():
    at = AppTest.from_file(str(PROJECT_ROOT / "app/views/overview.py"))
    at.run(timeout=30)
    at.button[0].click().run(timeout=60)
    assert not at.exception


def test_fault_page_does_not_leak_a_condition_into_the_session_config():
    """Regression: a run that ends while a disturbance is still active used to
    leave the modified ambient temperature in the shared session config."""
    at = AppTest.from_file(str(PROJECT_ROOT / "app/views/faults.py"))
    at.run(timeout=30)
    # Default kind is ambient_temp_step. Start at 50 min, last 30, total run 60:
    # the run ends while the disturbance is still active.
    at.slider[1].set_value(50)
    at.slider[2].set_value(30)
    at.slider[3].set_value(60)
    at.button[0].click().run(timeout=60)
    assert not at.exception
    assert at.session_state["config"].thermal.ambient_temp_c == 25.0
