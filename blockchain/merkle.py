#Merkle
from .crypto import sha256_hex

def merkle_root(lista_hashes: list[str]) -> str:
    if not lista_hashes:
        return sha256_hex(b"")

    nivel = list(lista_hashes)

    while len(nivel) > 1:
        if len(nivel) % 2 != 0:
            nivel.append(nivel[-1])

        siguiente_Nivel = []

        for i in range(0, len(nivel),2):
            izq = nivel[i]
            der = nivel[i + 1]
            padre = sha256_hex((izq + der).encode())
            siguiente_Nivel.add(padre)

    return siguiente_Nivel[0]