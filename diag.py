from blockchain.consensus.pow import ProofOfWork
from blockchain.block import Block, BlockHeader
from blockchain.transaction import Transaction
from blockchain.wallet import Wallet
import time

w = Wallet()
tx = Transaction(w.direccion(), w.direccion(), 0, {"x":1})
tx.firmar(w)

h = BlockHeader(version=1, prev_hash="0"*64, merkle_root=None, timestamp=0.0, difficulty=4, nonce=0, miner="TEST")
b = Block(h, [tx])
pow = ProofOfWork(difficulty=4)
print("before nonce:", b.hash[:16])
t=time.time()
pow.prepare_block(b, [])
print("after nonce :", b.hash[:16], "in", round(time.time()-t,2), "s")
print("nonce:", b.header.nonce)
print("starts 0000:", b.hash.startswith("0000"))
