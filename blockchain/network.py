import copy
from .node import Node
from .block import Block
from .transaction import Transaction


class Network:
    """Bus de mensajes en memoria."""

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}

    def register(self, node: Node) -> None:
        node.network = self
        self.nodes[node.node_id] = node

    def broadcast_tx(self, sender_id: str,
                     tx: Transaction) -> None:
        for nid, node in self.nodes.items():
            if nid != sender_id:
                node.receive_transaction(copy.deepcopy(tx))

    def broadcast_block(self, sender_id: str,
                        block: Block) -> None:
        for nid, node in self.nodes.items():
            if nid != sender_id:
                node.receive_block(copy.deepcopy(block))

    def __repr__(self) -> str:
        return f"Network({list(self.nodes.keys())})"