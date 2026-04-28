import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRADE_LENS_TESTS = ROOT / "Trade Lens" / "tests"


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str):
    for path in sorted(TRADE_LENS_TESTS.glob("test_*.py")):
        module_name = f"trade_lens_tests_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load tests from {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        tests.addTests(loader.loadTestsFromModule(module))
    return tests
