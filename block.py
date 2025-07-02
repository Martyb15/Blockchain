import time
import hashlib
import json

class Block:
    def __init__(self, index, transactions, previous_hash, timestamp=None):
        self.index = index
        self.transactions = transactions  # List of Transaction objects
        self.previous_hash = previous_hash
        self.timestamp = timestamp or time.time()
        self.number_used_once = 0
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        """Calculate the SHA-256 hash of the block's contents."""
        block_string = json.dumps({
            "index": self.index,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "number_used_once": self.number_used_once
        }, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()