import pytest
from looplocal import create_app, init_db


@pytest.fixture
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "test.sqlite"),
            "SECRET_KEY": "test-only-key",
        }
    )
    init_db(app)
    result = app.test_cli_runner().invoke(args=["seed-demo"])
    assert result.exit_code == 0, result.output
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth(client):
    def as_user(uid):
        with client.session_transaction() as s:
            s.clear()
            s["uid"] = uid
            s["csrf"] = "test-csrf"
        return client

    return as_user


@pytest.fixture
def post(client):
    def send(path, data=None, **kwargs):
        with client.session_transaction() as s:
            token = s.get("csrf", "test-csrf")
            s["csrf"] = token
        return client.post(path, data={"csrf": token, **(data or {})}, **kwargs)

    return send
