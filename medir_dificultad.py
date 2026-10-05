import os
import threading
import time
from blockchain.crypto import sha256_hex, canonical_json

N_NODOS = 4
CORRIDAS = 10
DIFICULTADES = [3, 4, 5]


def sha256(d):
    return sha256_hex(canonical_json(d))


def minar_una_vez(dificultad):
    fin = threading.Event()
    candado = threading.Lock()
    intentos = [0] * N_NODOS
    prefijo = "0" * dificultad
    # Contenido distinto en cada corrida para que no se repitan los resultados
    tx = {"proposito": "prueba", "contenido": os.urandom(8).hex()}

    def nodo(i):
        bloque = {
            "numero": 1,
            "nonce": i,
            "transaccion": tx,
            "hash_anterior": "0" * 64,
            "minero": f"Nodo {i}",
        }
        while not fin.is_set():
            h = sha256(bloque)
            intentos[i] += 1
            if h.startswith(prefijo):
                with candado:
                    if fin.is_set():
                        return
                    fin.set()
                return
            bloque["nonce"] += N_NODOS

    inicio = time.time()
    hilos = [threading.Thread(target=nodo, args=(i,)) for i in range(N_NODOS)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    return time.time() - inicio, sum(intentos)


if __name__ == "__main__":
    resumen = {}
    for d in DIFICULTADES:
        tiempos, intentos = [], []
        print(f"\n--- DIFICULTAD = {d} ---")
        for c in range(1, CORRIDAS + 1):
            t, n = minar_una_vez(d)
            tiempos.append(t)
            intentos.append(n)
            print(f"Corrida {c}: {t:.2f} s | {n} intentos")
        resumen[d] = (sum(tiempos) / CORRIDAS, sum(intentos) / CORRIDAS)

    print("\n=== TABLA PARA EL REPORTE ===")
    print("| Dificultad | Corridas | Tiempo promedio (s) | Intentos promedio |")
    print("|---|---|---|---|")
    for d, (t, n) in resumen.items():
        print(f"| {d} | {CORRIDAS} | {t:.2f} | {n:,.0f} |")

    print("\n=== COMPARACIÓN CON EL FACTOR 16 ===")
    print(f"Tiempo(4) / Tiempo(3) = {resumen[4][0] / resumen[3][0]:.1f}")
    print(f"Tiempo(5) / Tiempo(4) = {resumen[5][0] / resumen[4][0]:.1f}")
    print(f"Intentos(4) / Intentos(3) = {resumen[4][1] / resumen[3][1]:.1f}")
    print(f"Intentos(5) / Intentos(4) = {resumen[5][1] / resumen[4][1]:.1f}")
