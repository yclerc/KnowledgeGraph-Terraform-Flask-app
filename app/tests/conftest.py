"""
Fixtures for pytest
"""

import pytest
from app import app as flask_app
from models import model


@pytest.fixture
def app():
    """app fixture"""
    yield flask_app

@pytest.fixture
def client(app):
    """client fixture"""
    with app.test_client() as client:
        with app.app_context():
            # model.init_test_DB()
            model.init_db()
        yield client
