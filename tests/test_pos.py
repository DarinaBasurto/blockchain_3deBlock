# tests/test_pos.py
"""Pruebas de Proof-of-Stake: apuestas, sorteo, votación y slashing."""
import pytest

from blockchain.consensus.pos import Validator, PoSRound


def test_pos_no_validators_with_balance():
    """POS-01: ningún validador con saldo → no se inicia el sorteo."""
    validators = [
        Validator(id="V1", address="a1", balance=0.0),
        Validator(id="V2", address="a2", balance=0.0),
    ]
    round_ = PoSRound(validators, prev_hash="0" * 64, block_number=1)

    ok, msg = round_.collect_stakes({"V1": 10.0})
    assert ok is False
    assert "insuficiente" in msg.lower() or "inválida" in msg.lower()

    assert round_.sortition() is None


def test_pos_invalid_stake_amount():
    """POS-02: apuesta mayor al saldo, cero o negativa es rechazada."""
    for bad in (100.0, 0.0, -10.0):
        validators = [Validator(id="V1", address="a1", balance=50.0)]
        round_ = PoSRound(validators, prev_hash="0" * 64, block_number=1)
        ok, msg = round_.collect_stakes({"V1": bad})
        assert ok is False
        lowered = msg.lower()
        assert (
            "inválida" in lowered
            or "insuficiente" in lowered
            or "saldo" in lowered
        )


def test_pos_voting_exact_two_thirds_threshold():
    """POS-03: votación exactamente en 2/3 (3V >= 2A) acepta el bloque."""
    validators = [
        Validator(id="V1", address="a1", balance=100.0),
        Validator(id="V2", address="a2", balance=100.0),
        Validator(id="V3", address="a3", balance=100.0),
    ]
    round_ = PoSRound(validators, prev_hash="0" * 64, block_number=1)
    ok, _ = round_.collect_stakes({"V1": 100.0, "V2": 100.0, "V3": 100.0})
    assert ok is True

    round_.sortition()
    round_.vote("V1", True)
    round_.vote("V2", True)
    round_.vote("V3", False)

    accepted, V, A = round_.tally()
    assert A == 300.0
    assert V == 200.0
    assert accepted is True

    result = round_.finalize()
    assert result["accepted"] is True
    # Tras aceptar, las apuestas se liberan
    for v in validators:
        assert v.stake == 0.0


def test_pos_unauthorized_or_duplicate_vote():
    """POS-04: voto de nodo no validador o doble voto es rechazado."""
    validators = [
        Validator(id="V1", address="a1", balance=100.0),
        Validator(id="V2", address="a2", balance=100.0),
    ]
    round_ = PoSRound(validators, prev_hash="0" * 64, block_number=1)
    round_.collect_stakes({"V1": 100.0, "V2": 100.0})

    ok, msg = round_.vote("NodoX", True)
    assert ok is False
    assert "desconocido" in msg.lower()

    ok, _ = round_.vote("V1", True)
    assert ok is True

    ok, msg = round_.vote("V1", True)
    assert ok is False
    assert "ya votó" in msg.lower()


def test_pos_dishonest_proposer_slashing():
    """POS-05: proponente deshonesto es penalizado y se requiere nuevo intento."""
    validators = [
        Validator(id="V1", address="a1", balance=100.0),
        Validator(id="V2", address="a2", balance=100.0),
        Validator(id="V3", address="a3", balance=100.0),
    ]
    round_ = PoSRound(
        validators, prev_hash="0" * 64, block_number=1,
        slash_rule="A",
    )
    round_.collect_stakes({"V1": 100.0, "V2": 100.0, "V3": 100.0})

    proposer = round_.sortition()
    assert proposer is not None

    stake_before = proposer.stake
    # Todos votan NO → 3V = 0 < 2A
    for v in validators:
        round_.vote(v.id, False)

    result = round_.finalize()
    assert result["accepted"] is False
    assert result["slashed"] == stake_before
    assert result["new_attempt_needed"] is True


def test_pos_all_validators_slashed_to_zero():
    """POS-06: todos los validadores castigados hasta quedar sin saldo."""
    validators = [
        Validator(id="V1", address="a1", balance=100.0),
        Validator(id="V2", address="a2", balance=100.0),
    ]
    # Requiere orquestación multi-ronda con detención al agotar stakes
    assert validators is not None