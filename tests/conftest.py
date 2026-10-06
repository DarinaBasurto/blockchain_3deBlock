# tests/conftest.py
"""Fixtures compartidos para la suite de pruebas (Sección 5)."""
import pytest

from blockchain.wallet import Wallet
from blockchain.transaction import Transaction
from blockchain.network import Network
from blockchain.node import Node
from blockchain.consensus.pow import ProofOfWork
from blockchain.consensus.pos import Validator, PoSRound
from api.app import create_app


# ---------------------------------------------------------------------------
# Criptografía / wallets
# ---------------------------------------------------------------------------
@pytest.fixture
def fresh_wallet():
    """Retorna una Wallet Ed25519 recién generada."""
    return Wallet()


@pytest.fixture
def funded_wallet():
    """Retorna (Wallet, saldo contable simulado).

    No existe todavía un ledger por wallet en el core; se usa un saldo
    ficticio que los tests de negocio comparan contra `amount`.
    """
    wallet = Wallet()
    balance = 100.0
    return wallet, balance


# ---------------------------------------------------------------------------
# Transacciones
# ---------------------------------------------------------------------------
@pytest.fixture
def valid_transaction():
    """Factory: (sender_wallet, receiver_address, amount, data) -> Transaction firmada."""

    def _make(sender_wallet, receiver_address, amount=10.0, data=None):
        if data is None:
            data = {"tipo_declaracion": "inicial", "ejercicio": 2024}
        tx = Transaction(
            sender_wallet.direccion(), receiver_address, amount, data
        )
        tx.firmar(sender_wallet)
        return tx

    return _make


# ---------------------------------------------------------------------------
# Red / Nodos
# ---------------------------------------------------------------------------
@pytest.fixture
def fresh_network():
    """Factory: (num_nodes=4, difficulty=4) -> Network con ids N0..N{n-1}."""

    def _make(num_nodes=4, difficulty=4):
        network = Network()
        for i in range(num_nodes):
            node = Node(f"N{i}", ProofOfWork(difficulty=difficulty))
            network.register(node)
        return network

    return _make


@pytest.fixture
def chain_with_n_blocks():
    """Factory: (node, n=3) -> node con génesis + n bloques minados."""

    def _build(node, n=3):
        sender = Wallet()
        receiver = Wallet()
        for i in range(n):
            tx = Transaction(
                sender.direccion(),
                receiver.direccion(),
                1.0,
                {"i": i, "tipo_declaracion": "inicial", "ejercicio": 2024},
            )
            tx.firmar(sender)
            node.submit_transaction(tx)
            node.mine()
        return node

    return _build


# ---------------------------------------------------------------------------
# PoS
# ---------------------------------------------------------------------------
@pytest.fixture
def pos_validators_set():
    """Factory: (staked_amounts: dict[str,float]) -> list[Validator]."""

    def _make(staked_amounts):
        validators = []
        for vid, amount in staked_amounts.items():
            v = Validator(id=vid, address=f"addr_{vid}", balance=amount)
            validators.append(v)
        return validators

    return _make


# ---------------------------------------------------------------------------
# Flask
# ---------------------------------------------------------------------------
@pytest.fixture
def flask_client():
    """Cliente de pruebas de Flask (sin servidor en vivo)."""
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()