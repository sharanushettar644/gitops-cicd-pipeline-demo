from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_reports_service_info():
    body = client.get("/").json()
    assert body["service"] == "sample-api"
    assert "version" in body
    assert "environment" in body


def test_health_and_readiness_probes():
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json() == {"status": "ready"}


def test_item_lifecycle():
    created = client.post("/items", json={"name": "widget", "quantity": 3})
    assert created.status_code == 201
    item = created.json()
    assert item["name"] == "widget"
    assert item["quantity"] == 3

    fetched = client.get(f"/items/{item['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == item

    assert item in client.get("/items").json()

    assert client.delete(f"/items/{item['id']}").status_code == 204
    assert client.get(f"/items/{item['id']}").status_code == 404


def test_validation_rejects_bad_input():
    assert client.post("/items", json={"name": "", "quantity": 1}).status_code == 422
    assert client.post("/items", json={"name": "x", "quantity": -1}).status_code == 422


def test_missing_item_returns_404():
    assert client.get("/items/999999").status_code == 404
    assert client.delete("/items/999999").status_code == 404


def test_metrics_exposed_with_route_templates():
    client.get("/items/123456")
    text = client.get("/metrics").text
    assert "http_requests_total" in text
    assert 'path="/items/{item_id}"' in text
