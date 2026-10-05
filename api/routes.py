import copy
import threading
import time

from flask import (
    render_template,
    request,
    redirect,
    jsonify,
    flash
)

from blockchain.block import Block, BlockHeader
from blockchain.crypto import sha256_hex
from blockchain.wallet import Wallet
from blockchain.transaction import Transaction
from blockchain.network import Network
from blockchain.node import Node
from blockchain.consensus.pow import ProofOfWork


# =========================================================
# CONFIGURACIÓN
# =========================================================

DIFFICULTY = 5
REWARD = 50
NUM_NODES = 4


# =========================================================
# ESTADO GENERAL
# =========================================================

network = Network()

nodes = [
    Node(
        chr(ord("A") + i),
        ProofOfWork(difficulty=DIFFICULTY)
    )
    for i in range(NUM_NODES)
]

for node in nodes:
    network.register(node)


# Billeteras de ejemplo
alice = Wallet()
bob = Wallet()

wallets = {
    "Alice": alice,
    "Bob": bob,
}


# Estado de la carrera
mining_state = {
    "mining": False,
    "winner": None,
    "last_block_hash": None,
}


# Datos visuales de cada nodo
node_stats = {
    node.node_id: {
        "attempts": 0,
        "last_hash": "",
        "status": "Esperando",
        "reward": 0,
    }
    for node in nodes
}


# Event compartido por todos los mineros
stop_event = threading.Event()

# Evita que dos nodos se proclamen ganadores
winner_lock = threading.Lock()

# Protege las estadísticas que lee Flask
stats_lock = threading.Lock()

# Protege el estado global general (nodes, wallets, mining_state)
state_lock = threading.Lock()


# =========================================================
# REGLA ADICIONAL
# =========================================================

def viola_regla(tx, chain, aceptadas):
    """Un servidor público solo puede registrar UNA declaración
    inicial por ejercicio. Regresa True si la transacción la viola."""
    if tx.data.get("tipo_declaracion") != "inicial":
        return False

    previas = [
        t for b in chain[1:] for t in b.transactions
    ] + aceptadas

    return any(
        t.sender == tx.sender
        and t.data.get("tipo_declaracion") == "inicial"
        and t.data.get("ejercicio") == tx.data.get("ejercicio")
        for t in previas
    )


# =========================================================
# MINERÍA
# =========================================================

def mining_worker(node, node_index, transactions, prev_hash, timestamp):
    """
    Cada nodo busca un nonce distinto.

    Nodo A: 0, 4, 8, 12...
    Nodo B: 1, 5, 9, 13...
    Nodo C: 2, 6, 10, 14...
    Nodo D: 3, 7, 11, 15...
    """

    header = BlockHeader(
        version=1,
        prev_hash=prev_hash,
        merkle_root=None,
        timestamp=timestamp,
        difficulty=DIFFICULTY,
        nonce=node_index,
        miner=node.node_id,
    )

    candidate = Block(
        header,
        copy.deepcopy(transactions)
    )

    nonce = node_index
    attempts = 0
    prefix = "0" * DIFFICULTY

    with stats_lock:
        node_stats[node.node_id]["status"] = "Minando"
        node_stats[node.node_id]["attempts"] = 0
        node_stats[node.node_id]["last_hash"] = ""

    while not stop_event.is_set():

        candidate.header.nonce = nonce

        current_hash = candidate.compute_hash()

        attempts += 1

        # No hace falta bloquear el diccionario en absolutamente
        # cada intento. Actualizamos cada 500 intentos.
        if attempts % 500 == 0:
            with stats_lock:
                node_stats[node.node_id]["attempts"] = attempts
                node_stats[node.node_id]["last_hash"] = current_hash

        # ¿Encontramos PoW válido?
        if current_hash.startswith(prefix):

            with winner_lock:

                # Puede que otro hilo haya ganado un instante antes
                if stop_event.is_set():
                    return

                candidate.hash = current_hash

                # Verificación final usando EL MISMO consenso
                # que ya desarrolló el proyecto
                with state_lock:
                    chain_copy = list(node.chain)
                if not node.consensus.validate_block(
                    candidate,
                    chain_copy
                ):
                    return

                # Marcamos ganador ANTES de que otro hilo pueda entrar
                with state_lock:
                    mining_state["winner"] = node.node_id
                    mining_state["last_block_hash"] = current_hash

                with stats_lock:
                    node_stats[node.node_id]["attempts"] = attempts
                    node_stats[node.node_id]["last_hash"] = current_hash
                    node_stats[node.node_id]["status"] = "Ganador"
                    node_stats[node.node_id]["reward"] += REWARD

                # Detener a todos los demás
                stop_event.set()

                # Añade el bloque a este nodo.
                # receive_block lo difunde por Network a los demás.
                with state_lock:
                    node.receive_block(candidate)
                    mining_state["mining"] = False

                return

        # El nodo no prueba todos los enteros.
        # Avanza de NUM_NODES en NUM_NODES.
        nonce += NUM_NODES

    # Si salió porque otro nodo ganó
    with stats_lock:
        if node_stats[node.node_id]["status"] != "Ganador":
            node_stats[node.node_id]["attempts"] = attempts
            node_stats[node.node_id]["status"] = "Detenido"


def start_mining_race():
    """
    Prepara una carrera completa entre los cuatro nodos.
    """

    stop_event.clear()

    with state_lock:
        mining_state["mining"] = True
        mining_state["winner"] = None
        mining_state["last_block_hash"] = None
        source_node = nodes[0]
        transactions = copy.deepcopy(source_node.mempool)
        prev_hash = source_node.chain[-1].hash
        local_nodes = list(nodes)

    with stats_lock:
        for node in local_nodes:
            node_stats[node.node_id]["attempts"] = 0
            node_stats[node.node_id]["last_hash"] = ""
            node_stats[node.node_id]["status"] = "Preparando"

    # Misma marca de tiempo para todos.
    timestamp = time.time()

    threads = []

    for i, node in enumerate(local_nodes):

        thread = threading.Thread(
            target=mining_worker,
            args=(
                node,
                i,
                transactions,
                prev_hash,
                timestamp,
            ),
            daemon=True
        )

        threads.append(thread)
        thread.start()

    # Esperar a todos ocurre en este hilo coordinador,
    # NO en la petición HTTP.
    for thread in threads:
        thread.join()

    with state_lock:
        mining_state["mining"] = False


# =========================================================
# FLASK
# =========================================================

def register_routes(app):

    # -----------------------------------------------------
    # Página principal
    # -----------------------------------------------------

    @app.route("/")
    def index():
        with state_lock:
            local_nodes = list(nodes)
            main_node = nodes[0]
            chain = list(main_node.chain)
            mempool = list(main_node.mempool)
            valid = main_node.is_chain_valid()
            local_wallets = dict(wallets)
            is_mining = mining_state["mining"]
            winner = mining_state["winner"]

        with stats_lock:
            local_stats = copy.deepcopy(node_stats)

        return render_template(
            "index.html",
            nodes=local_nodes,
            chain=chain,
            mempool=mempool,
            valid=valid,
            wallets=local_wallets,
            mining=is_mining,
            winner=winner,
            stats=local_stats,
            difficulty=DIFFICULTY,
            reward=REWARD,
        )

    # -----------------------------------------------------
    # Crear transacción
    # -----------------------------------------------------

    @app.route("/transaccion", methods=["POST"])
    def create_transaction():

        with state_lock:
            is_mining = mining_state["mining"]

        if is_mining:
            flash(
                "Espera a que termine la minería antes de crear otra transacción.",
                "warning"
            )
            return redirect("/")

        sender_name = request.form["sender"]
        receiver_name = request.form["receiver"]

        try:
            amount = float(request.form["amount"])
        except ValueError:
            flash("El monto debe ser numérico.", "error")
            return redirect("/")

        try:
            ejercicio = int(request.form["ejercicio"])
        except ValueError:
            flash("El ejercicio debe ser un año numérico.", "error")
            return redirect("/")

        data = {
            "proposito": "declaraciones",
            "tipo_declaracion": request.form["tipo_declaracion"],
            "ejercicio": ejercicio,
            "hash_declaracion": sha256_hex(
                request.form.get("documento", "")
            ),
        }

        with state_lock:
            sender_wallet = wallets[sender_name]
            receiver_wallet = wallets[receiver_name]

        tx = Transaction(
            sender=sender_wallet.direccion(),
            receiver=receiver_wallet.direccion(),
            amount=amount,
            data=data,
        )

        tx.firmar(sender_wallet)

        with state_lock:
            accepted = nodes[0].submit_transaction(tx)

        if accepted:
            flash(
                "Transacción firmada y enviada a la red.",
                "success"
            )
        else:
            flash(
                "La transacción fue rechazada.",
                "error"
            )

        return redirect("/")

    # -----------------------------------------------------
    # Iniciar minería
    # -----------------------------------------------------

    @app.route("/minar", methods=["POST"])
    def mine():

        with state_lock:
            is_mining = mining_state["mining"]
            has_mempool = bool(nodes[0].mempool)

        if is_mining:
            flash(
                "Ya existe una carrera de minería activa.",
                "warning"
            )
            return redirect("/")

        if not has_mempool:
            flash(
                "No hay transacciones pendientes para minar.",
                "warning"
            )
            return redirect("/")

        # Validamos firma y regla adicional ANTES de lanzar los hilos
        aceptadas = []

        with state_lock:
            mempool_snapshot = list(nodes[0].mempool)
            chain_snapshot = list(nodes[0].chain)

        for tx in mempool_snapshot:

            if not tx.verify():
                motivo = "firma inválida"
            elif viola_regla(tx, chain_snapshot, aceptadas):
                motivo = (
                    "ya existe una declaración inicial de ese "
                    "ejercicio para este servidor público"
                )
            else:
                aceptadas.append(tx)
                continue

            with state_lock:
                for n in nodes:
                    n.mempool = [
                        t for t in n.mempool if t.tx_id != tx.tx_id
                    ]

            flash(f"Transacción rechazada: {motivo}.", "error")

        with state_lock:
            has_mempool_after = bool(nodes[0].mempool)

        if not has_mempool_after:
            return redirect("/")

        # Lanzamos la carrera en segundo plano.
        # Flask puede regresar la página inmediatamente.
        coordinator = threading.Thread(
            target=start_mining_race,
            daemon=True
        )

        coordinator.start()

        return redirect("/")

    # -----------------------------------------------------
    # Estado en vivo
    # -----------------------------------------------------

    @app.route("/estado")
    def status():

        with state_lock:
            is_mining = mining_state["mining"]
            winner = mining_state["winner"]
            last_block_hash = mining_state["last_block_hash"]
            local_nodes = list(nodes)
            node_snapshots = [
                {
                    "node_id": node.node_id,
                    "height": len(node.chain),
                    "mempool": len(node.mempool),
                    "valid": node.is_chain_valid(),
                }
                for node in local_nodes
            ]

        with stats_lock:
            node_data = []
            for ns in node_snapshots:
                node_id = ns["node_id"]
                stats = node_stats[node_id]
                node_data.append({
                    "id": node_id,
                    "attempts": stats["attempts"],
                    "last_hash": stats["last_hash"],
                    "status": stats["status"],
                    "reward": stats["reward"],
                    "height": ns["height"],
                    "mempool": ns["mempool"],
                    "valid": ns["valid"],
                })

        return jsonify({
            "mining": is_mining,
            "winner": winner,
            "last_block_hash": last_block_hash,
            "nodes": node_data,
        })

    # -----------------------------------------------------
    # Alterar bloque para demostrar validación
    # -----------------------------------------------------

    @app.route("/alterar", methods=["POST"])
    def tamper():

        with state_lock:
            is_mining = mining_state["mining"]

        if is_mining:
            flash(
                "No se puede alterar mientras los nodos están minando.",
                "warning"
            )
            return redirect("/")

        with state_lock:
            node = nodes[0]
            chain_len = len(node.chain)
            block = node.chain[1] if chain_len >= 2 else None

        if chain_len < 2:
            flash(
                "Primero debes minar al menos un bloque.",
                "warning"
            )
            return redirect("/")

        if not block or not block.transactions:
            flash(
                "El bloque no contiene transacciones.",
                "warning"
            )
            return redirect("/")

        # Alteramos SOLO la copia del Nodo A
        # sin recalcular firma, tx_id, Merkle ni hash.
        with state_lock:
            block.transactions[0].amount += 9999

        flash(
            "Se alteró una transacción del bloque 1 en el Nodo A. "
            "La validación ahora debe detectar el cambio.",
            "error"
        )

        return redirect("/")