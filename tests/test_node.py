# tests/test_node.py
"""Pruebas del nodo, mempool y validación de cadena (Categorías 1 y 2)."""
import pytest

from blockchain.node import Node
from blockchain.consensus.pow import ProofOfWork


def test_mine_empty_mempool(fresh_network):
    """TX-07: intentar minar con mempool vacía devuelve None y no altera la cadena."""
    network = fresh_network()
    node = network.nodes["N0"]
    assert len(node.mempool) == 0
    height_before = len(node.chain)

    result = node.mine()

    assert result is None
    assert len(node.chain) == height_before


def test_receive_shorter_or_invalid_chain(fresh_network, chain_with_n_blocks):
    """CH-02: cadena recibida más corta es rechazada; la cadena local se conserva."""
    network = fresh_network()
    node_a = network.nodes["N0"]
    chain_with_n_blocks(node_a, 5)
    assert len(node_a.chain) >= 4
    local_height = len(node_a.chain)

    isolated = Node("ISO", ProofOfWork(difficulty=4))
    assert len(isolated.chain) == 1

    result = node_a.receive_chain(isolated.chain)

    assert result is False
    assert len(node_a.chain) == local_height


def test_tamper_intermediate_block_invalidates_chain(
    fresh_network, chain_with_n_blocks
):
    """CH-03: manipular un bloque intermedio invalida la cadena completa."""
    network = fresh_network()
    node = network.nodes["N0"]
    chain_with_n_blocks(node, 4)
    assert node.is_chain_valid() is True

    block = node.chain[1]
    assert len(block.transactions) > 0

    # Manipular monto de la primera transacción del bloque 1
    block.transactions[0].amount = 9999.0

    assert node.is_chain_valid() is False