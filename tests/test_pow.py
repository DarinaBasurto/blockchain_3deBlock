# tests/test_pow.py
"""Pruebas de Proof-of-Work, fork resolution y maduración de recompensas."""
from types import SimpleNamespace

import pytest

from blockchain.ledger import compute_balances, available_of, REWARD


@pytest.mark.xfail(reason="pick_winner() not yet in repo")
def test_pow_two_winners_tie_breaking(fresh_network):
    """POW-01: dos ganadores en la misma ronda (desempate por hash menor)."""
    network = fresh_network()
    # Requiere función de desempate determinista todavía inexistente
    assert hasattr(network.nodes["N0"], "pick_winner")


@pytest.mark.xfail(reason="state_lock and /minar guards not yet in repo")
def test_concurrent_mining_request_rejected(flask_client):
    """POW-02: solicitar minado concurrente (carrera ya en progreso)."""
    r = flask_client.post("/minar")
    r2 = flask_client.post("/minar")
    assert r2.status_code in (400, 409)


@pytest.mark.xfail(reason="stop_event cancellation loop not implemented in testable way")
def test_pow_timeout_or_cancellation(fresh_network):
    """POW-03: dificultad excesiva → cancelación por stop_event o límite de rondas."""
    network = fresh_network()
    node = network.nodes["N0"]
    # Requiere un worker de minado cancelable
    assert hasattr(node.consensus, "stop_event")


def test_reward_maturity_requires_six_confirmations():
    """POW-04: recompensa consultada antes de 6 confirmaciones permanece pendiente."""
    miner = "MINER_ADDR"

    # Cadena: génesis + 3 bloques minados por `miner`
    chain = []
    for h in range(4):
        header = SimpleNamespace(miner=miner if h > 0 else "")
        blk = SimpleNamespace(header=header, transactions=[])
        chain.append(blk)

    bal = compute_balances(chain, maturity=6)
    # tip=3, todos los bloques minados están por debajo del umbral
    assert bal[miner]["pending"] == 3 * REWARD
    assert bal[miner]["available"] == 0.0

    # Extender a 10 bloques (tip=9)
    for h in range(4, 10):
        header = SimpleNamespace(miner=miner)
        blk = SimpleNamespace(header=header, transactions=[])
        chain.append(blk)

    bal = compute_balances(chain, maturity=6)
    # Bloques en h=1,2,3 maduraron (tip - h >= 6) → 3*REWARD disponibles
    # Bloques en h=4..9 siguen pendientes → 6*REWARD
    assert bal[miner]["available"] == 3 * REWARD
    assert bal[miner]["pending"] == 6 * REWARD


def test_available_of_unknown_address():
    """POW-04 (aux): address desconocida devuelve 0.0."""
    assert available_of("UNKNOWN", []) == 0.0


@pytest.mark.xfail(reason="coinbase reward transaction not yet in repo")
def test_fake_reward_amount_rejected(fresh_network):
    """POW-05: recompensa falsa (monto distinto al establecido) es rechazada."""
    network = fresh_network()
    node = network.nodes["N0"]
    # No existe concepto de coinbase en el core actual
    assert hasattr(node.consensus, "validate_reward")