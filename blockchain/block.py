from .crypto import sha256_hex, canonical_json
from .merkle import merkle_root
from .transaction import Transaction


class BlockHeader:

    def __init__(self, version, prev_hash, merkle_root,
                 timestamp, difficulty, nonce):
        self.version = version
        self.prev_hash = prev_hash
        self.merkle_root = merkle_root
        self.timestamp = timestamp
        self.difficulty = difficulty
        self.nonce = nonce

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "prev_hash": self.prev_hash,
            "merkle_root": self.merkle_root,
            "timestamp": self.timestamp,
            "difficulty": self.difficulty,
            "nonce": self.nonce,
        }


class Block:

    def __init__(self, header: BlockHeader,
                 transactions: list[Transaction]):
        self.header = header
        self.transactions = transactions

        if self.header.merkle_root is None:
            self.header.merkle_root = merkle_root(
                [tx.tx_id for tx in self.transactions]
            )

        self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        """Hash del bloque = SHA-256 del header serializado.
        Se recalcula cada vez que el header cambia (ej. durante el minado)."""
        return sha256_hex(canonical_json(self.header.to_dict()))

    def to_dict(self) -> dict:
        return {
            "header": self.header.to_dict(),
            "transactions": [tx.to_dict() for tx in self.transactions],
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Block":
        header = BlockHeader(**d["header"])
        txs = [Transaction.from_dict(t) for t in d["transactions"]]
        return cls(header, txs)

    def __repr__(self) -> str:
        return (f"Block(hash={self.hash[:10]}…, "
                f"txs={len(self.transactions)}, "
                f"nonce={self.header.nonce})")
