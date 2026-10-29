import re

import ethcensus


def test_version_is_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", ethcensus.__version__)


def test_package_docstring_lists_stages():
    for stage in ("collect", "fetch", "extract", "annotate", "classify", "analyze"):
        assert stage in ethcensus.__doc__
