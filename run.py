from blockchain.wallet import Wallet
from blockchain.transaction import Transaction
from blockchain.network import Network
from blockchain.node import Node
from blockchain.consensus.pow import ProofOfWork


def main():
    print("=== 3deBlock · Demo PoW ===\n")

    # 1. Red y nodos
    net = Network()
    nodos = [
        Node("A", ProofOfWork(difficulty=4, verbose=True)),
        Node("B", ProofOfWork(difficulty=4)),
        Node("C", ProofOfWork(difficulty=4)),
    ]
    for n in nodos:
        net.register(n)
    print(f"Red: {net}\n")

    # 2. Billeteras
    alice = Wallet()
    bob = Wallet()
    print(f"Alice  : {alice}")
    print(f"Bob    : {bob}\n")

    # 3. Transacciones firmadas
    tx1 = Transaction(alice.direccion(), bob.direccion(), 10,
                      "declaración inicial")
    tx1.firmar(alice)

    tx2 = Transaction(bob.direccion(), alice.direccion(), 3,
                      "modificación")
    tx2.firmar(bob)

    print(f"tx1: {tx1} · firma válida: {tx1.verify()}")
    print(f"tx2: {tx2} · firma válida: {tx2.verify()}\n")

    # 4. Enviar a nodo A
    nodos[0].submit_transaction(tx1)
    nodos[0].submit_transaction(tx2)
    print(f"A mempool: {len(nodos[0].mempool)} txs\n")

    # 5. Minar
    print("Minando bloque 1…")
    bloque = nodos[0].mine()
    print(f"Bloque minado: {bloque}\n")

    # 6. Estado de la red
    print("=== Estado tras el minado ===")
    for n in nodos:
        print(f"  {n} · cadena válida: {n.is_chain_valid()}")

    # 7. Manipulación
    print("\n=== Manipulando el bloque 1 en el nodo A ===")
    nodos[0].chain[1].transactions[0].amount = 9999
    print(f"  Nodo A tras manipular: válida = {nodos[0].is_chain_valid()}")
    print(f"  Nodo B intacto:        válida = {nodos[1].is_chain_valid()}")

    # 8. Firma inválida
    print("\n=== Transacción con firma inválida ===")
    tx_mala = Transaction(alice.direccion(), bob.direccion(), 100)
    tx_mala.firmar(alice)
    tx_mala.amount = 9999  # manipulación tras firmar
    print(f"  tx_mala.verify() = {tx_mala.verify()}")
    aceptada = nodos[2].submit_transaction(tx_mala)
    print(f"  Nodo C aceptó: {aceptada}")


if __name__ == "__main__":
    main()