# 3deBlock

Blockchain didáctica con dos mecanismos de consenso (**Proof-of-Work** y
**Proof-of-Stake**), una red en memoria de varios nodos y una interfaz web para
simular **declaraciones patrimoniales** firmadas con Ed25519.

## ¿De qué trata?

El proyecto implementa desde cero el núcleo de una blockchain (transacciones
firmadas, bloques con Merkle tree, PoW, cadena y mempool) y le agrega una capa
de simulación con UI web. El caso de uso es el registro de declaraciones
patrimoniales (uso "Moneda" con saldo y uso "Declaración" como registro puro),
y una carrera de minería entre varios nodos.

## Funciones principales

- Transacciones firmadas con Ed25519 y `tx_id` determinista (serialización canónica).
- Bloques con Merkle root y encadenamiento por hash.
- Proof-of-Work con carrera de minería multihilo entre nodos.
- Proof-of-Stake con selección de proponente, votación, penalizaciones y sorteo.
- Validación de integridad de la cadena y detección de manipulación (tamper demo).
- Regla de negocio: una sola declaración "inicial" por emisor y ejercicio.
- UI web con estado en vivo (bloques, mempool, saldos, nodos, bitácora, ronda PoS).
- Configuración en caliente de número de nodos, dificultad y modo (PoW/PoS).
- Demo CLI (`run.py`) para ver el ciclo completo sin interfaz.

## Cómo correr la interfaz

```bash
# 1. Entorno virtual (ya incluido en el repo) e instalar dependencias
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Levantar el servidor Flask
python -m api.app
# o, alternativamente:
flask --app api.app run --debug --no-reload
```

Abrir en el navegador: http://127.0.0.1:5000

Las dependencias de assets (fuentes, iconos, uPlot) ya están versionadas en
`api/static/`, por lo que no se necesita Node/Bun para ejecutar la interfaz.
Solo si se desean regenerar (`bun install && bun run build`).

## Otros comandos

```bash
python run.py            # Demo CLI del flujo completo
pytest                   # Tests
python medir_dificultad.py  # Benchmark de dificultad PoW
```

## Estructura

```
blockchain/   Núcleo (crypto, transaction, block, merkle, wallet, network, node, ledger, consensus/{pow,pos})
api/          Servidor Flask, rutas y assets de la UI
tests/        Pruebas
run.py        Demo CLI
```
