import csv
from pathlib import Path

import pytest

from maglimit.planner import explain
from maglimit.site import Site
from maglimit.telescope import Telescope

CASES = list(csv.DictReader((Path(__file__).parent/"golden_cases.csv").open(encoding="utf-8")))


def test_table_is_substantial():
    """Test that the golden table covers enough cases to be worth sharing.
    """
    assert len(CASES) >= 40


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c['object']}-bortle{c['bortle']}")
def test_golden_verdict(case):
    """Test a verdict against the reviewed table.
    """
    telescope = Telescope(float(case["aperture"]), float(case["fstop"]))
    site = Site(bortle=int(case["bortle"]))
    assert explain(case["object"], telescope, site)["verdict"] == case["verdict"]
