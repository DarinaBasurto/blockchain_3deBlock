import hashlib
import json

# Funcion hash que devuelve el texto en utf-8 transofrmado a hexadecimal
def sha256_hex(data: bytes) -> str:
    hash_hex = hashlib.sha256(data.encode("utf-8")).hexdigest()
    #print(f"Hasheando el siguiente texto: {text}")
    #print(hash_hex)
    return hash_hex


# Funcion que hace un objeto con claves ordenadas, sin espacios y que respeta UTF-8
def canonical_json(obj) -> bytes:
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",",":"),
        ensure_ascii=False,
    ).encode("utf-8")

