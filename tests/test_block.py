# tests/test_block.py
"""Pruebas de integridad de bloques (Categoría 2)."""
import pytest


def test_altered_block_hash_or_prev_hash(fresh_network, chain_with_n_blocks):
    """CH-01: bloque con hash o prev_hash alterado es rechazado por el consenso."""
    network = fresh_network()
    node = network.nodes["N0"]     
    chain_with_n_blocks(node, 2)
    assert len(node.chain) >= 3

    block = node.chain[1]
    original_hash = block.hash

    # Alterar hash almacenado
    block.hash = "f" * 64
    assert node.consensus.validate_block(block, node.chain) is False

    # Restaurar y alterar prev_hash (recalculando hash del header)
    block.hash = original_hash
    block.header.prev_hash = "0" * 64
    block.hash = block.compute_hash()
    assert node.consensus.validate_block(block, node.chain) is False