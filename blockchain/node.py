import time
from .block import Block, BlockHeader
from .transaction import Transaction
from .consensus.base import Consensus
from .wallet import verificar_firma

from blockchain.ledger import compute_balances, available_of

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .network import Network


class Node:
    """
    Nodo de la red.

    - chain: lista de bloques (empieza con génesis).
    - mempool: transacciones pendientes.
    - consensus: estrategia de consenso.
    - network: bus inyectado al registrar.
    """

    def __init__(self, node_id: str, consensus: Consensus) -> None:
        self.node_id = node_id
        self.consensus = consensus
        self.network: "Network | None" = None
        self.chain: list[Block] = [self._genesis()]
        self.mempool: list[Transaction] = []
        self.bootstrap_balance: dict = {}

    # ---------------- saldos ----------------

    def balance_of(self, address: str) -> float:
        return available_of(address, self.chain,
                            bootstrap=self.bootstrap_balance)

    def pending_of(self, address: str) -> float:
        entry = compute_balances(self.chain,
                                 bootstrap=self.bootstrap_balance).get(address)
        return entry["pending"] if entry else 0.0

    def can_spend(self, address: str, amount: float) -> bool:
        return amount > 0 and self.balance_of(address) >= amount

    # ---------------- génesis ----------------

    def _genesis(self) -> Block:
        header = BlockHeader(
            version=1,
            prev_hash="0" * 64,
            merkle_root=None,
            timestamp=0.0,
            difficulty=0,
            nonce=0,
        )
        return Block(header, [])

    # ---------------- transacciones ----------------

    def submit_transaction(self, tx: Transaction) -> bool:
        """Un cliente envía una transacción al nodo."""
        if not self._valid_transaction(tx):
            return False
        if tx.amount > 0:
            pending_out = sum(t.amount for t in self.mempool if t.sender == tx.sender)
            if pending_out + tx.amount > self.balance_of(tx.sender):
                return False
        self.mempool.append(tx)
        if self.network:
            self.network.broadcast_tx(self.node_id, tx)
        return True

    def receive_transaction(self, tx: Transaction) -> None:
        """Otro nodo difunde una transacción."""
        if not self._valid_transaction(tx):
            return
        if any(t.tx_id == tx.tx_id for t in self.mempool):
            return
        self.mempool.append(tx)

    def _valid_transaction(self, tx: Transaction) -> bool:
        if not tx.verify():
            return False
        if any(t.tx_id == tx.tx_id for t in self.mempool):
            return False
        if tx.amount > 0 and not self.can_spend(tx.sender, tx.amount):
            return False
        return True

    # ---------------- minado ----------------

    def mine(self) -> Block | None:
        accepted = []
        debits = {}
        for tx in self.mempool:
            if tx.amount > 0:
                prev = debits.get(tx.sender, 0.0)
                if prev + tx.amount > self.balance_of(tx.sender):
                    continue  # drop overspending tx
                debits[tx.sender] = prev + tx.amount
            accepted.append(tx)
        self.mempool = accepted

        if not self.mempool:
            return None

        header = BlockHeader(
            version=1,
            prev_hash=self.chain[-1].hash,
            merkle_root=None,
            timestamp=time.time(),
            difficulty=0,
            nonce=0,
        )
        block = Block(header, list(self.mempool))
        block = self.consensus.prepare_block(block, self.chain)

        self.chain.append(block)
        self._remove_from_mempool(block)

        if self.network:
            self.network.broadcast_block(self.node_id, block)
        return block

    # ---------------- recepción de bloques ----------------

    def receive_block(self, block: Block) -> None:
        if any(b.hash == block.hash for b in self.chain):
            return
        if not self.consensus.validate_block(block, self.chain):
            return

        self.chain.append(block)
        self._remove_from_mempool(block)

        if self.network:
            self.network.broadcast_block(self.node_id, block)

    def _remove_from_mempool(self, block: Block) -> None:
        ids = {tx.tx_id for tx in block.transactions}
        self.mempool = [t for t in self.mempool if t.tx_id not in ids]

    def receive_chain(self, blocks: list[Block]) -> bool:
        """
        Recibe una cadena candidata y la acepta si es más larga y válida.
        
        (1) rechaza si len(blocks) <= len(self.chain)
        (2) valida cada bloque más allá del génesis vía self.consensus.validate_block()
        (3) al tener éxito reemplaza self.chain y retorna True
        """
        if len(blocks) <= len(self.chain):
            return False

        current_chain = [blocks[0]]
        for b in blocks[1:]:
            if not self.consensus.validate_block(b, current_chain):
                return False
            current_chain.append(b)

        self.chain = blocks
        return True

    # ---------------- auditoría ----------------

    def is_chain_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            if not self.consensus.validate_block(
                self.chain[i], self.chain[:i]
            ):
                return False
        return True

    def __repr__(self) -> str:
        return (f"Node({self.node_id}, "
                f"altura={len(self.chain)}, "
                f"mempool={len(self.mempool)})")