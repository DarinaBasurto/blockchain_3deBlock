from .crypto import canonical_json, sha256_hex
import time

class Transaction:
    def __init__(self, sender, receiver, amount, data="", timestamp=None):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.data = data
        if timestamp is None:
            self.timestamp = time.time()
        else :
            self.timestamp = timestamp
        self.tx_id = self._hash_payload()

    def _hash_payload(self):
        objeto = {"sender": self.sender, "receiver": self.receiver, 
                  "amount": self.amount, "data": self.data, 
                  "timestamp": self.timestamp}
        return sha256_hex(canonical_json(objeto))

    def to_dict(self):
        return {"sender": self.sender, "receiver": self.receiver, 
                  "amount": self.amount, "data": self.data, 
                  "timestamp": self.timestamp, "tx_id": self.tx_id}

    @classmethod
    def from_dict(cls, d):
        return cls(
            sender=d["sender"],
            receiver=d["receiver"],
            amount=d["amount"],
            data=d.get("data",""),
            timestamp=d["timestamp"],
        )
    
    def verify(self):
        return self._hash_payload() == self.tx_id
