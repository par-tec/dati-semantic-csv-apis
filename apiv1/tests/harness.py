import contextlib
import logging


@contextlib.contextmanager
def log_records():
    """Fixture to capture log records during tests."""
    records = []

    class ListHandler(logging.Handler):
        def emit(self, record):
            records.append(record.getMessage())

    handler = ListHandler()
    logger = logging.getLogger()  # Root logger captures all logs
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    yield records
    logger.removeHandler(handler)


@contextlib.contextmanager
def client_harness(creator, config):
    """Fixture to create and yield the ASGI app with the given config."""
    with log_records() as logs:
        app = creator(config)
        with app.test_client() as client:
            # Allow test clients to send latin1 headers: See RFC9110.
            client._headers.encoding = "latin1"
            yield client, logs
