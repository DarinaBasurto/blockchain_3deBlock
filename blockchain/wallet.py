from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.exceptions import InvalidSignature

from .crypto import canonical_json


class Wallet:
    
    def __init__(self) -> None:
        self._private_key = ed25519.Ed25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()

    def firmar(self, tx_dict: dict) -> str:
        payload = {k: v for k, v in tx_dict.items() if k != "signature"}
        mensaje = canonical_json(payload)
        firma_bytes = self._private_key.sign(mensaje)
        return firma_bytes.hex()

    def direccion(self) -> str:
        pub_bytes = self._public_key.public_bytes(
            encoding=Encoding.Raw,
            format=PublicFormat.Raw,
        )
        return pub_bytes.hex()
    
    def __repr__(self) -> str:
        return f"Wallet({self.direccion()[:10]}…)"

def verificar_firma(tx_dict: dict, firma_hex: str) -> bool:
    try:
        pub_hex = tx_dict["sender"]
        pub_bytes = bytes.fromhex(pub_hex)
        pub = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)

        payload = {k: v for k, v in tx_dict.items() if k != "signature"}
        mensaje = canonical_json(payload)

        pub.verify(bytes.fromhex(firma_hex), mensaje)
        return True

    except (InvalidSignature, ValueError, KeyError, TypeError):
        return False