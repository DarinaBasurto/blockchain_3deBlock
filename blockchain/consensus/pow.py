import time
from .base import Consensus
from ..block import Block
from ..merkle import merkle_root


class ProofOfWork(Consensus):
    """
    PoW didáctico.
    Dificultad = número de ceros hexadecimales iniciales del hash.
    """

    def __init__(self, difficulty: int = 4, verbose: bool = False):
        self.difficulty = difficulty
        self.verbose = verbose

    def prepare_block(self, block: Block,
                      chain: list[Block]) -> Block:
        block.header.difficulty = self.difficulty
        block.header.nonce = 0
        prefix = "0" * self.difficulty
        start = time.time()

        while True:
            h = block.compute_hash()
            if h.startswith(prefix):
                block.hash = h
                if self.verbose:
                    dt = time.time() - start
                    print(f"  [PoW] {block.header.nonce} intentos "
                          f"({dt:.2f}s): {h[:16]}…")
                return block
            block.header.nonce += 1

    def validate_block(self, block: Block,
                       chain: list[Block]) -> bool:
        # 0. Hash guardado = hash recalculado
        if block.hash != block.compute_hash():
            return False

        # 1. Encadenamiento
        if chain and block.header.prev_hash != chain[-1].hash:
            return False

        # 2. Dificultad declarada
        if block.header.difficulty != self.difficulty:
            return False

        # 3. Hash cumple dificultad
        h = block.compute_hash()
        if not h.startswith("0" * self.difficulty):
            return False

        # 4. Raíz de Merkle corresponde
        expected = merkle_root([tx.tx_id for tx in block.transactions])
        if block.header.merkle_root != expected:
            return False

        # 5. Firma de cada transacción
        for tx in block.transactions:
            if not tx.verify():
                return False

        return True

    def select_chain(self,
                     candidates: list[list[Block]]) -> list[Block]:
        # Didáctico: cadena más larga
        return max(candidates, key=len)