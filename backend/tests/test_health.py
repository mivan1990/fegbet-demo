"""Faza 0: schelet functional."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_scanner_paths_blocked(client: TestClient) -> None:
    for path in ("/.env", "/.git/config", "/wp-admin/", "/index.php", "/dump.sql", "/x.bak"):
        resp = client.get(path)
        assert resp.status_code == 404, path


def test_normal_unknown_route_is_404_not_blocked(client: TestClient) -> None:
    resp = client.get("/api/chestie-inexistenta")
    assert resp.status_code == 404


def test_openapi_available(client: TestClient) -> None:
    assert client.get("/openapi.json").status_code == 200
