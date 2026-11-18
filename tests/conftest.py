"""
Pytest configuration and marker registration for DWM Circuit Compiler E2E tests.
"""

def pytest_configure(config):
    config.addinivalue_line("markers", "tier1: Tier 1 feature coverage tests")
    config.addinivalue_line("markers", "tier2: Tier 2 boundary and corner case tests")
    config.addinivalue_line("markers", "tier3: Tier 3 cross-feature combinations and invariants")
    config.addinivalue_line("markers", "tier4: Tier 4 real-world application scenarios and seed calibration")
    config.addinivalue_line("markers", "tier5: Tier 5 adversarial routing and serialization stress tests")
