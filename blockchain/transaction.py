from .crypto import canonical_json, sha256_hex
from .wallet import verificar_firma
import time


class Transaction:
    def __init__(
        self,
        sender: str,
        receiver: str,
        amount: float,
        data: dict = None,
        timestamp: float | None = None,
        tx_id: str | None = None,
    ):
        """
        Representa una transacción en la blockchain.
        
        Invariant:
        - data debe ser obligatoriamente un diccionario (dict).
        - Si tx_id es provisto, debe coincidir exactamente con el hash del payload.
        """
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.data = {} if data is None else data
        self.timestamp = time.time() if timestamp is None else timestamp
        computed_tx_id = self._hash_payload()
        if tx_id is not None and tx_id != computed_tx_id:
            raise ValueError("tx_id mismatch")
        self.tx_id = computed_tx_id
        self.signature = ""

    def _hash_payload(self) -> str:
        objeto = {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "data": self.data,
            "timestamp": self.timestamp,
        }
        return sha256_hex(canonical_json(objeto))

    def firmar(self, wallet) -> None:
        self.signature = wallet.firmar(self.to_dict())

    def verify(self) -> bool:
        return verificar_firma(self.to_dict(), self.signature)

    def to_dict(self) -> dict:
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "data": self.data,
            "timestamp": self.timestamp,
            "tx_id": self.tx_id,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Transaction":
        tx = cls(
            sender=d["sender"],
            receiver=d["receiver"],
            amount=d["amount"],
            data=d.get("data", {}),
            timestamp=d["timestamp"],
            tx_id=d.get("tx_id"),
        )
        tx.signature = d.get("signature", "")
        return tx

    def __repr__(self) -> str:
        return f"Tx({self.sender[:8]}…→{self.receiver[:8]}…: {self.amount})"