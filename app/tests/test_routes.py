"""
test scenarii for app
# NB: make sure to populate the DB with at least 1 file before testing
"""
import json


def test_index_0(client):
    """test landing page for uploads"""
    res = client.get("/")
    assert res.status_code == 200
    assert b"Upload new File" in res.data


def test_index_1(app, client):
    """test upload file"""
    client = app.test_client()
    data = {
        "file": (b"this is a test", "test_file.pdf"),
    }
    res = client.post("/", data=data, follow_redirects=True)
    assert res.status_code == 200


def test_document(client):
    """test document info"""
    res = client.get("/documents/1")
    data = json.loads(res.get_data(as_text=True))
    # The status must be 200 OK
    assert res.status_code == 200
    # We test if we received the ID of the JSON object
    assert data["Text ID"] == 1


def test_text(client):
    """test document content"""
    res = client.get("/text/1")
    data = json.loads(res.get_data(as_text=True))
    # The status must be 200 OK
    assert res.status_code == 200
    # We test if we received the ID of the JSON object
    assert data["Text ID"] == 1
