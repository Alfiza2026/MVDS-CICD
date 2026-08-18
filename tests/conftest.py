import sys
import os
import importlib
import pytest

PROVIDER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "provider"))
CONSUMER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "consumer"))


def _load_app(path):
    original = sys.modules.pop("app", None)
    sys.path.insert(0, path)
    module = importlib.import_module("app")
    sys.path.remove(path)
    sys.modules.pop("app", None)
    if original:
        sys.modules["app"] = original
    return module


_provider_module = _load_app(PROVIDER_PATH)
_consumer_module = _load_app(CONSUMER_PATH)


@pytest.fixture
def provider_client():
    _provider_module.app.config["TESTING"] = True
    with _provider_module.app.test_client() as client:
        yield client


@pytest.fixture
def consumer_client():
    _consumer_module.app.config["TESTING"] = True
    with _consumer_module.app.test_client() as client:
        yield client


@pytest.fixture
def consumer_module():
    return _consumer_module
