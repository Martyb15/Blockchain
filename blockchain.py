import time, hashlib, json, random
from typing import List, Dict
from block import Block, merkle_root
from transaction import Transaction
from config import DIFFICULTY, BLOCK_REWARD, STAKE_REWARD_PCT, JSON_SEP


class Blockchain:
    def __init__(self, use_pos: bool = False):
        self.chain: List[Block] = []
        self.pending: List[Transaction] = []
        self.accounts: Dict[str, dict] = {}      # {addr: {"balance": int, "nonce": int, "stake": int}}
        self.use_pos = use_pos
        self.create_genesis_block()

    # ---------- helper -----------
    def _get_acct(self, addr: str) -> dict:
        return self.accounts.setdefault(addr, {"balance": 0, "nonce": 0, "stake": 0})

    # ---------- genesis ----------
    def create_genesis_block(self):
        genesis = Block(index=0, previous_hash="0")
        genesis.hash = genesis.compute_hash()
        self.chain.append(genesis)

    # ---------- transaction pool ----------
    def add_tx(self, tx: Transaction) -> bool:
        acct = self._get_acct(tx.sender)
        # 1. signature / nonce / funds checks
        if not tx.verify():
            print("⚠️  bad signature")
            return False
        if tx.nonce != acct["nonce"] + 1:
            print("⚠️  bad nonce")
            return False
        needed = tx.amount + tx.fee
        if tx.tx_type in ("PAY", "OPEN_REMIT", "STAKE"):
            if acct["balance"] < needed:
                print("⚠️  insufficient funds")
                return False
        # all good
        self.pending.append(tx)
        acct["nonce"] += 1
        return True

    # ---------- mining / validation ----------
    def _mine_pow(self, block: Block):
        target = "0" * DIFFICULTY
        while True:
            block.hash = block.compute_hash()
            if block.hash.startswith(target):
                break
            block.nonce += 1

    def _select_pos_validator(self) -> str:
        stake_table = [(addr, acct["stake"]) for addr, acct in self.accounts.items() if acct["stake"]]
        total = sum(s for _, s in stake_table)
        if not total:
            return random.choice(list(self.accounts) or ["coinbase"])  # fallback
        r = random.uniform(0, total)
        upto = 0
        for addr, stake in stake_table:
            upto += stake
            if upto >= r:
                return addr
        return stake_table[-1][0]

    def mine_block(self, miner_addr: str) -> Block | None:
        if not self.pending:
            print("No tx to mine")
            return None

        # reward tx
        reward_tx = Transaction(
            tx_type="PAY",
            sender="COINBASE",
            recipient=miner_addr,
            amount=BLOCK_REWARD,
            fee=0,
            nonce=0,
            signature="GENESIS",
        )
        block_txs = self.pending[:]
        block_txs.append(reward_tx)

        last = self.chain[-1]
        blk = Block(index=last.index + 1, previous_hash=last.hash, transactions=block_txs)

        if self.use_pos:
            validator = self._select_pos_validator()
            if validator != miner_addr:
                print("⛔ not selected in this PoS round")
                return None
            blk.hash = blk.compute_hash()  # no heavy work
            # PoS inflation
            self._get_acct(miner_addr)["balance"] += int(BLOCK_REWARD * STAKE_REWARD_PCT)
        else:
            self._mine_pow(blk)

        # commit state
        self._apply_block(blk)
        self.pending.clear()
        self.chain.append(blk)
        return blk

    def _apply_block(self, blk: Block):
        # naive state changes
        for tx in blk.transactions:
            sender = self._get_acct(tx.sender)
            if tx.tx_type == "PAY":
                if tx.sender != "COINBASE":
                    sender["balance"] -= tx.amount + tx.fee
                recipient = self._get_acct(tx.recipient)
                recipient["balance"] += tx.amount
            elif tx.tx_type == "STAKE":
                sender["balance"] -= tx.amount
                sender["stake"] += tx.amount
            elif tx.tx_type == "UNSTAKE":
                sender["stake"] -= tx.amount
                sender["balance"] += tx.amount
            # fees to miner are already in BLOCK_REWARD for simplicity

    # ---------- chain validation for new nodes ----------
    def is_valid_chain(self) -> bool:
        for i, blk in enumerate(self.chain[1:], 1):
            prev = self.chain[i - 1]
            if blk.previous_hash != prev.hash:
                return False
            if not blk.hash.startswith("0" * DIFFICULTY) and not self.use_pos:
                return False
            if blk.hash != blk.compute_hash():
                return False
        return True
