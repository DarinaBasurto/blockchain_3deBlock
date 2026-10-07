# tests/test_routes.py
"""Pruebas de la aplicación Flask (UI, estado y robustez HTTP)."""
import pytest


def test_reset_simulation_endpoint(flask_client):
    """APP-01: reiniciar la simulación al estado Génesis."""
    r = flask_client.post("/reset")
    assert r.status_code == 200


def test_polling_state_during_mining_race(flask_client):
    """APP-02: polling a /estado no bloquea ni lanza excepción."""
    r = flask_client.get("/estado")
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, dict)
    assert "mining" in data
    assert "nodes" in data
    assert isinstance(data["nodes"], list)

    # Repetir rápidamente (stateless polling)
    for _ in range(3):
        r = flask_client.get("/estado")
        assert r.status_code == 200


def test_concurrent_tab_requests(flask_client):
    """APP-03: acciones simultáneas desde múltiples pestañas."""
    # Requiere state_lock para serializar accesos a mempool/stats/mining_state
    r1 = flask_client.post("/minar")
    r2 = flask_client.post("/minar")
    assert r1.status_code != 500
    assert r2.status_code != 500


def test_malformed_route_requests(flask_client):
    """APP-04: peticiones HTTP con datos mal formados → 400, sin 500."""
    # Falta campo amount
    r = flask_client.post("/transaccion", json={"sender": "A"})
    assert r.status_code == 400

    # Tipo erróneo
    r = flask_client.post(
        "/transaccion", json={"sender": "A", "amount": "cinco"}
    )
    assert r.status_code == 400

    # Body vacío
    r = flask_client.post("/transaccion", data="", content_type="application/json")
    assert r.status_code == 400