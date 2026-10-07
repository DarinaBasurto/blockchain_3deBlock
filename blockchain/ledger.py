"""Pure ledger helpers: aggregate balances over a chain of blocks.

No project imports; blocks/transactions are accessed by duck typing.
"""
import sys

REWARD = 50.0


def compute_balances(chain: list, maturity: int = 6,
                     bootstrap: dict | None = None) -> dict:
    """Return {address: {"available", "pending", "sent", "received"}}.

    Block at index h (genesis=0) rewards its miner with REWARD. The
    reward counts as available once at least `maturity` blocks sit on
    top of it, i.e. (len(chain)-1-h) >= maturity; otherwise it stays
    pending. Every transaction adds its amount to sender.sent and to
    receiver.received. available = received + matured_rewards - sent,
    clamped at 0 (a warning is written to stderr on clamp).
    """
    bal: dict[str, dict[str, float]] = {}
    matured: dict[str, float] = {}

    def b(addr):
        if addr not in bal:
            bal[addr] = dict(available=0.0, pending=0.0,
                             sent=0.0, received=0.0)
            matured[addr] = 0.0
        return bal[addr]

    tip = len(chain) - 1
    for h, blk in enumerate(chain):
        miner = blk.header.miner
        if miner:
            if tip - h >= maturity:
                b(miner)
                matured[miner] += REWARD
            else:
                b(miner)["pending"] += REWARD
        for tx in blk.transactions:
            b(tx.sender)["sent"] += tx.amount
            b(tx.receiver)["received"] += tx.amount

    if bootstrap:
        for addr, amt in bootstrap.items():
            if amt <= 0:
                continue
            entry = b(addr)
            entry["received"] += amt

    for addr, d in bal.items():
        raw = d["received"] + matured[addr] - d["sent"]
        if raw < 0:
            print(f"warning: clamping negative balance for "
                  f"{addr!r}: {raw}", file=sys.stderr)
            raw = 0.0
        d["available"] = raw

    return bal


def available_of(address: str, chain: list, maturity: int = 6,
                 bootstrap: dict | None = None) -> float:
    """Return the available balance of `address`, or 0.0 if unknown."""
    entry = compute_balances(chain, maturity, bootstrap).get(address)
    return entry["available"] if entry else 0.0