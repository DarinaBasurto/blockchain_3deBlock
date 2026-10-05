import hashlib
from dataclasses import dataclass


@dataclass
class Validator:
    """Nodo validador con saldo propio y apuesta bloqueada por ronda."""

    id: str
    address: str
    balance: float
    stake: float = 0.0

    def can_stake(self, amount: float) -> bool:
        """True si `amount` es una apuesta válida para este validador."""
        return amount > 0 and amount <= self.balance

    def apply_stake(self, amount: float) -> None:
        """Bloquea `amount` del saldo disponible como apuesta."""
        if not self.can_stake(amount):
            raise ValueError(f"Apuesta inválida para {self.id}: {amount}")
        self.balance -= amount
        self.stake += amount

    def slash(self, amount: float) -> float:
        """Recorta hasta `amount` de la apuesta; devuelve lo castigado real."""
        if amount <= 0:
            return 0.0
        actual = min(amount, self.stake)
        self.stake -= actual
        return actual

    def release_stake(self) -> None:
        """Devuelve la apuesta restante al saldo disponible."""
        self.balance += self.stake
        self.stake = 0.0


class PoSRound:
    """
    Ronda de Proof of Stake: apuestas → sorteo → candidato → votación.

    El sorteo es ponderado por apuesta y reproducible a partir de
    (prev_hash, block_number, attempt). La votación pesa por valor
    acumulado y se acepta si 3V >= 2A. Si se rechaza, el proponente
    es castigado según la regla elegida y se requiere otro intento.
    """

    def __init__(self, validators: list[Validator], prev_hash: str,
                 block_number: int, attempt: int = 0,
                 alpha: float = 0.5, slash_rule: str = "A"):
        if slash_rule not in ("A", "B"):
            raise ValueError(f"Regla de castigo inválida: {slash_rule}")
        if slash_rule == "B" and not (0 < alpha <= 1):
            raise ValueError(f"alpha fuera de rango: {alpha}")
        self.validators = list(validators)
        self.prev_hash = prev_hash
        self.block_number = block_number
        self.attempt = attempt
        self.alpha = alpha
        self.slash_rule = slash_rule
        self.proposer: Validator | None = None
        self.votes: dict[str, bool] = {}
        self.state = "APUESTAS"

    # -------- Fase 1: apuestas -------------------------------------------
    def collect_stakes(self, stakes: dict[str, float]) -> tuple[bool, str]:
        """Valida y bloquea las apuestas. Devuelve (ok, mensaje)."""
        by_id = {v.id: v for v in self.validators}
        for vid, amount in stakes.items():
            v = by_id.get(vid)
            if v is None:
                return False, f"Validador desconocido: {vid}"
            if amount <= 0:
                return False, f"Apuesta inválida de {vid}: debe ser > 0"
            if amount > v.balance:
                return False, f"Saldo insuficiente para {vid}"
        for vid, amount in stakes.items():
            by_id[vid].apply_stake(amount)
        self.state = "SORTEO"
        return True, "Apuestas registradas"

    # -------- Fase 2: sorteo ponderado -----------------------------------
    def sortition(self) -> Validator | None:
        """Elige al proponente con probabilidad proporcional a su apuesta."""
        active = sorted(
            (v for v in self.validators if v.stake > 0),
            key=lambda v: v.id,
        )
        total = sum(v.stake for v in active)
        if total <= 0:
            return None
        seed = f"{self.prev_hash}|{self.block_number}|{self.attempt}".encode()
        r = int(hashlib.sha256(seed).hexdigest(), 16) % total
        acc = 0.0
        for v in active:
            acc += v.stake
            if r < acc:
                self.proposer = v
                self.state = "CANDIDATO"
                return v
        return None

    # -------- Fase 3: votación -------------------------------------------
    def vote(self, validator_id: str, yes: bool) -> tuple[bool, str]:
        """Registra un voto pesado por apuesta. Devuelve (ok, mensaje)."""
        by_id = {v.id: v for v in self.validators}
        v = by_id.get(validator_id)
        if v is None:
            return False, f"Validador desconocido: {validator_id}"
        if v.stake <= 0:
            return False, f"{validator_id} no es validador en esta ronda"
        if validator_id in self.votes:
            return False, f"{validator_id} ya votó"
        self.votes[validator_id] = yes
        self.state = "VOTACION"
        return True, "Voto registrado"

    def tally(self) -> tuple[bool, float, float]:
        """Cuenta votos. Devuelve (aceptado, V, A)."""
        A = sum(v.stake for v in self.validators)
        V = sum(v.stake for v in self.validators if self.votes.get(v.id))
        return (3 * V >= 2 * A, V, A)

    # -------- Fase 4: cierre ---------------------------------------------
    def finalize(self, total_tx_value: float = 0.0) -> dict:
        """Cierra la ronda: libera apuestas o castiga al proponente."""
        accepted, _, _ = self.tally()
        proposer_id = self.proposer.id if self.proposer else None
        slashed = 0.0
        new_attempt = False

        if accepted:
            self.state = "ACEPTADO"
            for v in self.validators:
                v.release_stake()
        else:
            self.state = "RECHAZADO"
            if self.proposer is not None and self.proposer.stake > 0:
                slashed = self.proposer.slash(
                    self._slash_amount(total_tx_value)
                )
            for v in self.validators:
                v.release_stake()
            new_attempt = True

        return {
            "accepted": accepted,
            "proposer_id": proposer_id,
            "slashed": slashed,
            "new_attempt_needed": new_attempt,
        }

    def _slash_amount(self, total_tx_value: float) -> float:
        """Castigo según la regla configurada (A o B)."""
        ap = self.proposer.stake
        if self.slash_rule == "B":
            return min(ap, self.alpha * total_tx_value)
        return ap