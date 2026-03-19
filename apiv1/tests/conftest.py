def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "performance: mark tests intended for benchmarking or perf checks",
    )
