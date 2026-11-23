"""Sample API used to demonstrate the CI/CD and GitOps pipeline.

Small on purpose: health probes, Prometheus metrics, and a tiny in-memory
CRUD resource are enough to exercise tests, image builds, scans, and
Kubernetes rollouts.
"""

import os
import time
from threading import Lock

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field

APP_VERSION = os.getenv("APP_VERSION", "dev")
ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

app = FastAPI(title="sample-api", version=APP_VERSION)

REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
)


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    # Use the route template (e.g. /items/{item_id}) to keep label cardinality low.
    route = request.scope.get("route")
    path = getattr(route, "path", "unmatched")
    LATENCY.labels(request.method, path).observe(time.perf_counter() - start)
    REQUESTS.labels(request.method, path, str(response.status_code)).inc()
    return response


class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    quantity: int = Field(ge=0, default=1)


class Item(ItemIn):
    id: int


_items: dict[int, Item] = {}
_next_id = 1
_lock = Lock()


@app.get("/")
def root() -> dict:
    return {"service": "sample-api", "version": APP_VERSION, "environment": ENVIRONMENT}


@app.get("/healthz")
def healthz() -> dict:
    """Liveness: the process is up."""
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict:
    """Readiness: ready to receive traffic."""
    return {"status": "ready"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/items")
def list_items() -> list[Item]:
    return list(_items.values())


@app.post("/items", status_code=201)
def create_item(payload: ItemIn) -> Item:
    global _next_id
    with _lock:
        item = Item(id=_next_id, **payload.model_dump())
        _items[item.id] = item
        _next_id += 1
    return item


@app.get("/items/{item_id}")
def get_item(item_id: int) -> Item:
    if item_id not in _items:
        raise HTTPException(status_code=404, detail="item not found")
    return _items[item_id]


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int) -> Response:
    with _lock:
        if _items.pop(item_id, None) is None:
            raise HTTPException(status_code=404, detail="item not found")
    return Response(status_code=204)
