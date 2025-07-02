from dataclasses import dataclass, field
from typing import List
import hashlib, json, time
from config import JSON_SEP
from transaction import Transaction


def merkle_root(tx_hashes: list[str]) -> str:
    """
    Very small, non-optimized Merkle tree (suitable for demo).
    """
    if not tx_hashes:
        return hashlib.sha256(b"").hexdigest()

    layer = tx_hashes
    while len(layer) > 1:
        if len(layer) % 2:            # odd → duplicate last
            layer.append(layer[-1])
        layer = [
            hashlib.sha256((layer[i] + layer[i + 1]).encode()).hexdigest()
            for i in range(0, len(layer), 2)
        ]
    return layer[0]


@dataclass()
class Block:
    index: int
    previous_hash: str
    timestamp: float = field(default_factory=time.time)
    transactions: List[Transaction] = field(default_factory=list)
    nonce: int = 0
    merkle_root: str = ""
    hash: str = ""

    # ------------------------------------------------
    def compute_hash(self) -> str:
        block_dict = {
            "idx": self.index,
            "prev": self.previous_hash,
            "ts": self.timestamp,
            "nonce": self.nonce,
            "mrkl": self.merkle_root or merkle_root([tx.hash() for tx in self.transactions]),
        }
        block_json = json.dumps(block_dict, sort_keys=True, separators=JSON_SEP)
        return hashlib.sha256(block_json.encode()).hexdigest()