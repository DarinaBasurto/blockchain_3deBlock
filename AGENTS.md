# AGENTS.md — Documentación técnica para modelos de IA

## Decisiones congeladas (2026-10-05)

1. `canonical_json` ([blockchain/crypto.py](file:///home/sayi/Documents/SEM_9/Blockhain/blockchain_3deBlock/blockchain/crypto.py)) es la ÚNICA serialización utilizada para hashear y firmar. Prohibido usar `json.dumps(..., sort_keys=True)` directamente para hashear o firmar en cualquier parte del código. Los parámetros de `canonical_json` están congelados (`sort_keys=True`, `separators=(",",":")`, `ensure_ascii=False`, codificación UTF-8).

2. `Transaction.data` es SIEMPRE un `dict`, nunca `str`. [run.py](file:///home/sayi/Documents/SEM_9/Blockhain/blockchain_3deBlock/run.py) debe actualizarse en consecuencia. Invariante documentado explícitamente.

3. `tx_id` es determinista a partir de `{sender, receiver, amount, data, timestamp}`. `Transaction.__init__` recibe un parámetro opcional `tx_id`. Si se proporciona, DEBE ser igual a `_hash_payload()` o lanzar `ValueError`. `from_dict` pasa el `tx_id` almacenado para detectar manipulaciones en el momento de la reconstrucción.

4. `ProofOfWork.select_chain()` se conectará en `Node.receive_chain()` (ver Prompt 2, Tarea D). Hasta entonces, no debe eliminarse.

5. `mining_worker()` en [api/routes.py](file:///home/sayi/Documents/SEM_9/Blockhain/blockchain_3deBlock/api/routes.py) omite intencionalmente `Node.mine()` para la carrera de minería. Llama directamente a `node.consensus.validate_block()`. Mantener este comportamiento.

6. Todas las lecturas/escrituras a `mining_state`, `node_stats`, `nodes` y `wallets` en [api/routes.py](file:///home/sayi/Documents/SEM_9/Blockhain/blockchain_3deBlock/api/routes.py) DEBEN estar protegidas por `stats_lock`, `winner_lock` o un nuevo `state_lock`.

7. Balance and double-spend checks apply ONLY to transactions with amount > 0. Transactions with amount == 0 are treated as pure registry entries (declaraciones) and are exempt, matching the guide's intent that the 'saldo suficiente' rule is purpose-specific to the 'Moneda' use case.

## 1. Resumen del proyecto

Blockchain didáctica con Proof-of-Work, carrera de minería multihilo entre 4 nodos, y UI web Flask para simular declaraciones patrimoniales.

- **Lenguaje**: Python 3.14 (venv incluido).
- **Dependencias**: Flask, Flask-Cors, cryptography, pytest.
- **Estado**: El core blockchain (transacciones firmadas Ed25519, bloques con Merkle tree, PoW, red en memoria, validación de cadena) funciona end-to-end. La UI Flask con carrera de minería concurrente funciona. Proof-of-Authority (`poa.py`) es un archivo vacío.

## 2. Estructura de directorios

```
.
├── blockchain/
│   ├── __init__.py          → Re-exporta Transaction, Block, BlockHeader, Wallet, verificar_firma, Node, Network
│   ├── block.py             → Clases BlockHeader y Block
│   ├── transaction.py       → Clase Transaction (creación, firma, verificación, serialización)
│   ├── wallet.py            → Clase Wallet (keypair Ed25519) y función verificar_firma
│   ├── crypto.py            → Funciones sha256_hex y canonical_json
│   ├── merkle.py            → Función merkle_root
│   ├── network.py           → Clase Network (bus de mensajes en memoria)
│   ├── node.py              → Clase Node (cadena, mempool, minado, validación)
│   └── consensus/
│       ├── __init__.py      → Re-exporta Consensus y ProofOfWork
│       ├── base.py          → ABC Consensus (interfaz abstracta)
│       ├── pow.py           → Clase ProofOfWork (implementación PoW)
│       └── poa.py           → Vacío (no implementado)
├── api/
│   ├── __init__.py          → Vacío
│   ├── app.py               → Factory Flask (create_app) y módulo ejecutable
│   ├── routes.py            → Rutas Flask, carrera de minería multihilo, estado global
│   ├── static/
│   │   ├── app.js           → JS del frontend (polling de /estado)
│   │   └── style.css        → Estilos
│   └── templates/
│       └── index.html       → Template Jinja2
├── tests/
│   ├── __init__.py          → Vacío
│   ├── test_block.py        → Stub vacío
│   ├── test_merkle.py       → Stub vacío
│   ├── test_network.py      → Stub vacío
│   ├── test_node.py         → Stub vacío
│   ├── test_pow.py          → Stub vacío
│   └── test_transaction.py  → Stub vacío
├── run.py                   → Demo CLI (crea red, firma, mina, manipula)
├── medir_dificultad.py      → Benchmark de dificultad PoW (script independiente)
├── requirements.txt         → pytest, Flask, Flask-Cors, cryptography
├── pyproject.toml           → Vacío
├── .env.example             → Vacío
├── .env                     → Existe (no versionado)
├── .gitignore
└── README.md
```

## 3. Módulos y responsabilidades

### `blockchain/crypto.py`

| Función | Firma | Descripción | Importado por |
|---|---|---|---|
| `sha256_hex` | `(data: bytes \| str) -> str` | SHA-256 hex digest. Si recibe `str`, codifica a UTF-8. | `block.py`, `merkle.py`, `transaction.py`, `api/routes.py` |
| `canonical_json` | `(obj) -> bytes` | `json.dumps` con `sort_keys=True`, `separators=(",",":")`, `ensure_ascii=False`, codificado a UTF-8. Retorna `bytes`. | `block.py`, `transaction.py`, `wallet.py` |

### `blockchain/merkle.py`

| Función | Firma | Descripción | Importado por |
|---|---|---|---|
| `merkle_root` | `(lista_hashes: list[str]) -> str` | Merkle root binario. Si lista vacía, retorna `sha256_hex(b"")`. Duplica último elemento si longitud impar. Concatena pares como strings y hashea con `sha256_hex((izq + der).encode())`. | `block.py`, `pow.py` |

### `blockchain/wallet.py`

**Clase `Wallet`**

| Método | Firma | Descripción |
|---|---|---|
| `__init__` | `(self) -> None` | Genera keypair Ed25519 (`cryptography.hazmat`). |
| `firmar` | `(self, tx_dict: dict) -> str` | Firma `canonical_json(payload)` excluyendo clave `"signature"` del dict. Retorna firma como hex string. |
| `direccion` | `(self) -> str` | Public key raw bytes como hex string (32 bytes = 64 chars hex). |

Importado por: `transaction.py`, `api/routes.py`, `run.py`.

**Función `verificar_firma`**

```python
def verificar_firma(tx_dict: dict, firma_hex: str) -> bool
```

Reconstruye la public key desde `tx_dict["sender"]` (hex), computa `canonical_json(payload)` excluyendo `"signature"`, y verifica con Ed25519. Retorna `False` ante cualquier excepción (`InvalidSignature`, `ValueError`, `KeyError`, `TypeError`).

Importado por: `transaction.py`, `node.py`, `blockchain/__init__.py`.

### `blockchain/transaction.py`

**Clase `Transaction`**

| Método | Firma | Descripción |
|---|---|---|
| `__init__` | `(self, sender, receiver, amount, data="", timestamp=None)` | `timestamp` default `time.time()`. Calcula `tx_id` automáticamente vía `_hash_payload()`. Inicializa `signature = ""`. |
| `_hash_payload` | `(self) -> str` | `sha256_hex(canonical_json({sender, receiver, amount, data, timestamp}))`. Genera el `tx_id`. |
| `firmar` | `(self, wallet) -> None` | Llama `wallet.firmar(self.to_dict())`. Almacena resultado en `self.signature`. |
| `verify` | `(self) -> bool` | Llama `verificar_firma(self.to_dict(), self.signature)`. |
| `to_dict` | `(self) -> dict` | Retorna dict con 7 claves: `sender`, `receiver`, `amount`, `data`, `timestamp`, `tx_id`, `signature`. |
| `from_dict` | `(cls, d: dict) -> Transaction` | Classmethod. Reconstruye Transaction desde dict. **Nota**: `tx_id` se recalcula internamente por `__init__` (no se toma del dict). |

Importado por: `block.py`, `node.py`, `network.py`, `api/routes.py`, `run.py`.

### `blockchain/block.py`

**Clase `BlockHeader`**

| Método | Firma | Descripción |
|---|---|---|
| `__init__` | `(self, version, prev_hash, merkle_root, timestamp, difficulty, nonce, miner="")` | Almacena todos los campos. `miner` es opcional, default `""`. |
| `to_dict` | `(self) -> dict` | Dict con 7 claves: `version`, `prev_hash`, `merkle_root`, `timestamp`, `difficulty`, `nonce`, `miner`. |

**Clase `Block`**

| Método | Firma | Descripción |
|---|---|---|
| `__init__` | `(self, header: BlockHeader, transactions: list[Transaction])` | Si `header.merkle_root is None`, lo calcula desde `[tx.tx_id for tx in transactions]`. Calcula `self.hash` vía `compute_hash()`. |
| `compute_hash` | `(self) -> str` | `sha256_hex(canonical_json(self.header.to_dict()))`. Solo hashea el header, no las transacciones. |
| `to_dict` | `(self) -> dict` | Dict con 3 claves: `header`, `transactions`, `hash`. |
| `from_dict` | `(cls, d: dict) -> Block` | Classmethod. Reconstruye via `BlockHeader(**d["header"])` y `Transaction.from_dict()`. |

Importado por: `node.py`, `network.py`, `pow.py`, `api/routes.py`, `run.py`.

### `blockchain/node.py`

**Clase `Node`**

| Método | Firma | Descripción |
|---|---|---|
| `__init__` | `(self, node_id: str, consensus: Consensus) -> None` | Crea cadena con bloque génesis. `network` inicia como `None`. |
| `_genesis` | `(self) -> Block` | Bloque con `prev_hash="0"*64`, `timestamp=0.0`, `difficulty=0`, `nonce=0`, sin transacciones, `merkle_root=None` (se calcula en Block.__init__). |
| `submit_transaction` | `(self, tx: Transaction) -> bool` | Valida tx (firma + no duplicada en mempool), agrega a mempool, broadcast via network. Retorna `True`/`False`. |
| `receive_transaction` | `(self, tx: Transaction) -> None` | Desde otro nodo. Valida y agrega si no está duplicada. |
| `_valid_transaction` | `(self, tx: Transaction) -> bool` | Verifica `tx.verify()` y que `tx_id` no exista en mempool. |
| `mine` | `(self) -> Block \| None` | Retorna `None` si mempool vacía. Crea bloque con todas las tx de mempool, llama `consensus.prepare_block()`, agrega a cadena, limpia mempool, broadcast. |
| `receive_block` | `(self, block: Block) -> None` | Si hash no duplicado y `consensus.validate_block()` pasa, agrega a cadena y broadcast. |
| `_remove_from_mempool` | `(self, block: Block) -> None` | Elimina de mempool las tx incluidas en el bloque (por `tx_id`). |
| `is_chain_valid` | `(self) -> bool` | Valida todos los bloques (excepto génesis) con `consensus.validate_block()`. |

Importado por: `network.py`, `api/routes.py`, `run.py`.

### `blockchain/network.py`

**Clase `Network`**

| Método | Firma | Descripción |
|---|---|---|
| `__init__` | `(self) -> None` | Dict `nodes: dict[str, Node]` vacío. |
| `register` | `(self, node: Node) -> None` | Asigna `node.network = self`, agrega al dict. |
| `broadcast_tx` | `(self, sender_id: str, tx: Transaction) -> None` | `copy.deepcopy(tx)` a todos los nodos excepto el emisor. Llama `node.receive_transaction()`. |
| `broadcast_block` | `(self, sender_id: str, block: Block) -> None` | `copy.deepcopy(block)` a todos los nodos excepto el emisor. Llama `node.receive_block()`. |

Importado por: `api/routes.py`, `run.py`.

### `blockchain/consensus/base.py`

**ABC `Consensus`**

```python
class Consensus(ABC):
    @abstractmethod
    def prepare_block(self, block: Block, chain: list[Block]) -> Block: ...
    @abstractmethod
    def validate_block(self, block: Block, chain: list[Block]) -> bool: ...
    @abstractmethod
    def select_chain(self, candidates: list[list[Block]]) -> list[Block]: ...
```

Importado por: `node.py`, `pow.py`.

### `blockchain/consensus/pow.py`

**Clase `ProofOfWork(Consensus)`**

| Método | Firma | Descripción |
|---|---|---|
| `__init__` | `(self, difficulty: int = 4, verbose: bool = False)` | Almacena dificultad y flag verbose. |
| `prepare_block` | `(self, block: Block, chain: list[Block]) -> Block` | Fija `header.difficulty`, itera `nonce` desde 0 hasta encontrar hash con `difficulty` ceros hex iniciales. Mutación in-place + retorno. |
| `validate_block` | `(self, block: Block, chain: list[Block]) -> bool` | 5 checks: (1) hash almacenado == recalculado, (2) encadenamiento `prev_hash`, (3) dificultad declarada == esperada, (4) hash cumple dificultad, (5) merkle_root correcto, (6) firma de cada tx. |
| `select_chain` | `(self, candidates: list[list[Block]]) -> list[Block]` | `max(candidates, key=len)` (cadena más larga). |

Importado por: `api/routes.py`, `run.py`, `blockchain/consensus/__init__.py`.

### `api/app.py`

| Función | Firma | Descripción |
|---|---|---|
| `create_app` | `() -> Flask` | Factory. Secret key hardcodeada `"3deblock-dev-key"`. Importa y registra rutas. |

Variable de módulo: `app = create_app()`.

### `api/routes.py`

Función principal: `register_routes(app)` registra todas las rutas Flask.

**Estado global** (instanciado al importar el módulo):
- `DIFFICULTY = 5`, `REWARD = 50`, `NUM_NODES = 4`.
- `network`: instancia `Network` con 4 nodos (ids `"A"`, `"B"`, `"C"`, `"D"`).
- `wallets`: dict `{"Alice": Wallet(), "Bob": Wallet()}`.
- `mining_state`: dict con claves `mining`, `winner`, `last_block_hash`.
- `node_stats`: dict por `node_id` con `attempts`, `last_hash`, `status`, `reward`.
- Locks: `stop_event` (threading.Event), `winner_lock`, `stats_lock`.

**Funciones auxiliares**:

| Función | Firma | Descripción |
|---|---|---|
| `viola_regla` | `(tx, chain, aceptadas)` | Regla de negocio: un sender solo puede tener una declaración `"inicial"` por ejercicio. Accede a `tx.data` como dict. |
| `mining_worker` | `(node, node_index, transactions, prev_hash, timestamp)` | Worker de hilo. Cada nodo prueba nonces `node_index, node_index+NUM_NODES, ...`. Actualiza stats cada 500 intentos. |
| `start_mining_race` | `()` | Coordina la carrera: prepara estado, lanza `NUM_NODES` hilos, espera con `join()`. |

## 4. Estructuras de datos clave

### Transaction

| Campo | Tipo | Notas |
|---|---|---|
| `sender` | `str` | Ed25519 public key como hex (64 chars). |
| `receiver` | `str` | Ed25519 public key como hex (64 chars). |
| `amount` | `float` | Monto de la transacción. |
| `data` | `str \| dict` | String en core; dict en la API (`{proposito, tipo_declaracion, ejercicio, hash_declaracion}`). |
| `timestamp` | `float` | Unix timestamp. |
| `tx_id` | `str` | SHA-256 de `canonical_json({sender, receiver, amount, data, timestamp})`. |
| `signature` | `str` | Ed25519 firma hex. Inicialmente `""`. |

**Qué se hashea para tx_id**: `canonical_json` de `{sender, receiver, amount, data, timestamp}` (5 campos, sin `tx_id` ni `signature`).

**Qué se firma**: `canonical_json` del `to_dict()` completo (7 campos) excluyendo la clave `"signature"`. Es decir, se firma sobre `{sender, receiver, amount, data, timestamp, tx_id}` (6 campos).

### BlockHeader

| Campo | Tipo | Notas |
|---|---|---|
| `version` | `int` | Siempre `1`. |
| `prev_hash` | `str` | Hash del bloque anterior. Génesis: `"0"*64`. |
| `merkle_root` | `str \| None` | Se calcula en `Block.__init__` si es `None`. |
| `timestamp` | `float` | Unix timestamp. Génesis: `0.0`. |
| `difficulty` | `int` | Cantidad de ceros hex iniciales requeridos. Génesis: `0`. |
| `nonce` | `int` | Valor iterado durante el minado. |
| `miner` | `str` | ID del nodo minero. Default `""`. |

### Block

| Campo | Tipo | Notas |
|---|---|---|
| `header` | `BlockHeader` | |
| `transactions` | `list[Transaction]` | |
| `hash` | `str` | `sha256_hex(canonical_json(header.to_dict()))`. Solo el header se hashea. |

**Fórmula del hash del bloque**: `SHA-256(canonical_json(header.to_dict()))`. Las transacciones participan indirectamente vía `merkle_root` en el header.

### Wallet

| Campo | Tipo | Notas |
|---|---|---|
| `_private_key` | `Ed25519PrivateKey` | Generada en `__init__`. No serializable. |
| `_public_key` | `Ed25519PublicKey` | Derivada de `_private_key`. |

### Node

| Campo | Tipo | Notas |
|---|---|---|
| `node_id` | `str` | Identificador (e.g. `"A"`, `"B"`). |
| `consensus` | `Consensus` | Estrategia inyectada. |
| `network` | `Network \| None` | Se inyecta al registrar con `Network.register()`. |
| `chain` | `list[Block]` | Inicia con bloque génesis. |
| `mempool` | `list[Transaction]` | Transacciones pendientes. |

## 5. Interfaces y contratos

### ABC `Consensus` (en `blockchain/consensus/base.py`)

```python
@abstractmethod
def prepare_block(self, block: Block, chain: list[Block]) -> Block
@abstractmethod
def validate_block(self, block: Block, chain: list[Block]) -> bool
@abstractmethod
def select_chain(self, candidates: list[list[Block]]) -> list[Block]
```

### Implementaciones

| Clase | Archivo | Estado |
|---|---|---|
| `ProofOfWork` | `blockchain/consensus/pow.py` | Implementa los 3 métodos |
| (PoA) | `blockchain/consensus/poa.py` | Archivo vacío, no implementado |

### Quién llama qué

- `Node.mine()` llama `consensus.prepare_block()`.
- `Node.receive_block()` y `Node.is_chain_valid()` llaman `consensus.validate_block()`.
- `consensus.select_chain()` no se usa en ningún lugar del código actual.
- En `api/routes.py`, `mining_worker` llama `node.consensus.validate_block()` directamente (no vía Node).

## 6. Rutas Flask

| Método | Ruta | Entrada | Salida |
|---|---|---|---|
| GET | `/` | — | `render_template("index.html", ...)` con chain, mempool, wallets, stats |
| POST | `/transaccion` | Form: `sender`, `receiver`, `amount`, `ejercicio`, `tipo_declaracion`, `documento` (opcional) | Redirect a `/` con flash message |
| POST | `/minar` | — | Lanza carrera de minería en thread, redirect a `/` |
| GET | `/estado` | — | JSON: `{mining, winner, last_block_hash, nodes: [{id, attempts, last_hash, status, reward, height, mempool, valid}]}` |
| POST | `/alterar` | — | Modifica `amount` de la primera tx del bloque 1 en nodo A (+9999), redirect a `/` |

## 7. Convenciones del proyecto

- **Idioma de nombres**: Mixto. Clases y métodos de interfaz en inglés (`Block`, `Transaction`, `compute_hash`, `verify`). Métodos internos en español (`firmar`, `direccion`, `verificar_firma`, `viola_regla`). Variables locales en español (`nivel`, `siguiente_nivel`, `candado`).
- **Serialización canónica**: `canonical_json(obj)` retorna `bytes` (no `str`). Usa `sort_keys=True`, `separators=(",",":")`, `ensure_ascii=False`, `.encode("utf-8")`.
- **Hash del bloque**: `sha256_hex(canonical_json(header.to_dict()))`. Solo se hashea el header. Las transacciones participan vía `merkle_root`.
- **Firma de transacción**: Se firma `canonical_json(payload)` donde `payload = {k:v for k,v in tx_dict.items() if k != "signature"}`. El `tx_dict` incluye `tx_id`. Algoritmo: Ed25519 puro (sin prehash).
- **Cálculo de tx_id**: `sha256_hex(canonical_json({sender, receiver, amount, data, timestamp}))`. Solo 5 campos, sin `tx_id` ni `signature`.
- **Merkle root**: Concatenación de strings (`izq + der`), no de bytes. Se codifica con `.encode()` antes de hashear.
- **Génesis**: `prev_hash="0"*64`, `timestamp=0.0`, `difficulty=0`, `nonce=0`, `merkle_root=sha256_hex(b"")` (calculado, no hardcodeado), sin transacciones, `miner=""`.
- **Deep copy en red**: `Network` hace `copy.deepcopy()` de transacciones y bloques antes de enviar a otros nodos.
- **Dificultad en API vs CLI**: La API usa `DIFFICULTY=5`; `run.py` usa `difficulty=4`.

## 8. Qué está implementado y qué no

| Feature | Estado |
|---|---|
| Transaction con firma Ed25519 | ✅ funcional |
| Cálculo de tx_id | ✅ funcional |
| Block con Merkle tree | ✅ funcional |
| BlockHeader serialización/hash | ✅ funcional |
| Block.from_dict / to_dict | ✅ funcional |
| Wallet (generación keypair Ed25519) | ✅ funcional |
| Verificación de firma (verificar_firma) | ✅ funcional |
| Proof-of-Work (minado + validación 5 checks) | ✅ funcional |
| Node con mempool y cadena | ✅ funcional |
| Network (broadcast en memoria con deepcopy) | ✅ funcional |
| Carrera de minería multihilo (4 nodos) | ✅ funcional |
| Flask UI con polling de /estado | ✅ funcional |
| Regla de negocio viola_regla (declaración única) | ✅ funcional |
| Demostración de tamper (ruta /alterar) | ✅ funcional |
| select_chain (resolución de forks) | ⚠️ parcial — implementado en ProofOfWork pero nunca invocado |
| Proof-of-Authority | ❌ no existe — archivo `poa.py` vacío |
| Persistencia de cadena a disco | ❌ no existe |
| Networking real (TCP/HTTP entre nodos) | ❌ no existe (solo en memoria) |
| Wallet con importar/exportar clave | ❌ no existe |
| Ajuste dinámico de dificultad | ❌ no existe |
| Recompensa de minería como transacción coinbase | ❌ no existe (solo contador en `node_stats`) |
| Balance de wallets | ❌ no existe |
| API REST para consultas programáticas (fuera de /estado) | ❌ no existe |
| Tests unitarios | ❌ no existe — 6 archivos stub vacíos (0 bytes) |

## 9. Cómo correr el proyecto

```bash
# Instalar dependencias (venv ya incluido en el repo)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Demo CLI
python run.py

# Servidor Flask (UI web)
python -m api.app
# o
flask --app api.app run --debug --no-reload

# Tests
pytest

# Benchmark de dificultad
python medir_dificultad.py
```

Variables de entorno: `.env.example` y `.env` existen pero están vacíos. No se leen en el código.

## 10. Errores comunes y trampas

1. **No cambiar el orden de campos en `canonical_json`**: Usa `sort_keys=True`, por lo que el orden en el dict fuente no importa. Pero si cambias los nombres de las claves o agregas/quitas campos, rompes todos los hashes existentes y las firmas.

2. **tx_id se recalcula en `Transaction.__init__`**: Al llamar `Transaction.from_dict(d)`, el `tx_id` del dict original se ignora; se recalcula desde los 5 campos. Si `data` cambia de tipo (str vs dict), el `tx_id` será diferente.

3. **`data` tiene dos tipos**: En `run.py` es `str`; en `api/routes.py` es `dict`. `canonical_json` serializa ambos, pero producen hashes distintos. `viola_regla()` asume que `tx.data` es un `dict` (llama `tx.data.get()`). Mezclar tipos rompe la regla de negocio.

4. **Firma incluye `tx_id`**: `Wallet.firmar()` recibe `to_dict()` (que incluye `tx_id`) y excluye solo `"signature"`. Si se modifica `_hash_payload()` cambiará el `tx_id` y por tanto la firma será inválida.

5. **Block.hash se asigna en `__init__`**: Cambiar el header después de construir el Block sin recalcular `self.hash` deja el hash desactualizado. `compute_hash()` no actualiza `self.hash` automáticamente, solo retorna el valor. El minado en `ProofOfWork.prepare_block()` reasigna `block.hash = h` explícitamente.

6. **Minería en `api/routes.py` no usa `Node.mine()`**: La carrera multihilo implementa su propio loop de minado en `mining_worker()`, bypass directo al consenso. Solo llama `node.consensus.validate_block()` y `node.receive_block()` tras encontrar un nonce válido.

7. **`select_chain()` no se invoca**: Está implementado en `ProofOfWork` pero ningún código lo llama. No hay resolución de forks real.

8. **Estado mutable compartido en `api/routes.py`**: Los dicts `mining_state`, `node_stats`, la lista `nodes` y el dict `wallets` son globals mutables. Acceso protegido parcialmente por `stats_lock` y `winner_lock`, pero `nodes[0].mempool` se lee sin lock desde las rutas Flask.

9. **`poa.py` está vacío**: Importarlo no falla, pero instanciar una clase de PoA sí. El `consensus/__init__.py` no lo exporta.

10. **La dificultad de PoW es fija por instancia**: `validate_block()` rechaza bloques cuya `header.difficulty` no coincida con `self.difficulty`. Si dos nodos tienen instancias de `ProofOfWork` con distinta dificultad, rechazarán mutuamente sus bloques.

## Ultima actualizacion

- **Fecha**: 2026-10-05
- **Commit**: `3bbad83b78d884cde2b882cc5a4fca6cf556e42e`
- **Cambios recientes**: Archivo `AGENTS.md` creado por primera vez. Documentación generada a partir de inspección exhaustiva del código fuente en el commit indicado.
