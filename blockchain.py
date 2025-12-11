"""
Martin Barrios

blockchain.py
Core ledger + consensus engine for the micro-remittance demo chain.

Features
--------
- Proof-of-Work (default) or Proof-of-Stake toggle
- ECDSA-signed transactions, nonces, fee/reward handling
- Balances + optional staking ledger
- Remittance escrow contracts  (OPEN_REMIT / CLAIM_REMIT)


Things To Add                              Status
-------------                              ------
- Nonce and Balance Display                [In Progress]
- Persistent Storage                       [X]
- Secure Signing                           [X]
- P2P Persistence                          [X]
- Transaction History                      [X]
- Input Validation                         [X]
- Automated Tests                          [X]
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import time
from dataclasses import dataclass, replace
from typing import Dict, List

from block import Block, merkle_root
from config import BLOCK_REWARD, DIFFICULTY, JSON_SEP, STAKE_REWARD_PCT, REWARD_SENDER, REWARD_SIGNATURE

from transaction import Transaction

# -----------------------------------------------------------------------------#
#   New: Remittance dataclass
# -----------------------------------------------------------------------------#


@dataclass(frozen=True)
class Remittance:
    id: str
    sender: str
    recipient: str
    amount: int
    release_hash: str
    released: bool = False


# -----------------------------------------------------------------------------#
#   Blockchain
# -----------------------------------------------------------------------------#


class Blockchain:
    def __init__(self, use_pos: bool = False, enable_reward: bool = False):
        self.chain: List[Block] = []
        self.pending: List[Transaction] = []
        # account -> {"balance": int, "nonce": int, "stake": int}
        self.accounts: Dict[str, Dict[str, int]] = {}
        # NEW: id -> Remittance
        self.remits: Dict[str, Remittance] = {}
        self.use_pos = use_pos
        self.enable_reward = enable_reward
        self.create_genesis_block()
        self._last_signed: Dict[str, int] = {}

    # ---------------------------------------------------------------------#
    #  Helpers
    # ---------------------------------------------------------------------#

    def _get_acct(self, addr: str) -> Dict[str, int]:
        ''' Return (or create) the per-address balance/nonce/stake dict. '''
        return self.accounts.setdefault(addr, {"balance": 0, "nonce": 0, "stake": 0})

    # ---------------------------------------------------------------------#
    #  Genesis
    # ---------------------------------------------------------------------#

    def create_genesis_block(self):
        genesis = Block(index=0, previous_hash="0")
        genesis.hash = genesis.compute_hash()
        self.chain.append(genesis)

    # ---------------------------------------------------------------------#
    #  Transaction pool
    # ---------------------------------------------------------------------#

    def add_tx(self, tx: Transaction) -> bool:
        acct = self._get_acct(tx.sender)

        # tx-type allow-list
        if tx.tx_type not in {
            "PAY",
            "OPEN_REMIT",
            "CLAIM_REMIT",
            "STAKE",
            "UNSTAKE",
        }:
            print("!  unknown tx type")
            return False

        # 1) Signature
        if not tx.verify():
            print("!  bad signature")
            return False

        # 2) Nonce
        if tx.nonce != acct["nonce"] + 1:
            print("!  bad nonce")
            return False

        # 3) Funds
        needed = tx.amount + tx.fee
        if tx.tx_type in ("PAY", "OPEN_REMIT", "STAKE"):
            if acct["balance"] < needed:
                print("!  insufficient funds")
                return False

        # All good -> enqueue
        self.pending.append(tx)
        acct["nonce"] += 1
        return True

    # ---------------------------------------------------------------------#
    #  Mining / PoW or PoS
    # ---------------------------------------------------------------------#

    def _mine_pow(self, block: Block):
        target = "0" * DIFFICULTY
        while True:
            block.hash = block.compute_hash()
            if block.hash.startswith(target):
                break
            block.nonce += 1


    def _select_pos_validator(self) -> str:
        '''   Pick a validator weighted by stake, including any pending STAKE txs
    so that newly‐staked tokens count immediately for this round. '''
  
        # 1) Build a list of (address, effective_stake)
        stake_entries: list[tuple[str, int]] = []
        for addr, acct in self.accounts.items():
            base_stake = acct["stake"]
            # include any pending STAKE txs for this addr
            pending_stake = sum(
                tx.amount
                for tx in self.pending
                if tx.tx_type == "STAKE" and tx.sender == addr
            )
            effective = base_stake + pending_stake
            if effective > 0:
                stake_entries.append((addr, effective))

        # 2) If nobody has any stake, fall back to a random account
        total = sum(s for _, s in stake_entries)
        if total == 0:
            return random.choice(list(self.accounts) or ["coinbase"])

        # 3) Choose a random point in [0, total)
        r = random.uniform(0, total)
        upto = 0
        for addr, stake in stake_entries:
            upto += stake
            if upto >= r:
                return addr

        # 4) Fallback (shouldn't really happen)
        return stake_entries[-1][0]


    # ---------------------------------------------------------------------#
    #  Mining entry
    # ---------------------------------------------------------------------#

    def mine_block(self, miner_addr: str) -> Block | None:
        ''' Assemble pending transactions into a new block, optionally include the
    mining reward, run consensus (PoW or PoS), apply state changes, and
    append to the chain. '''
    

        if not self.pending:
            print("No tx to mine")
            return None

        # 1) Collect pending transactions
        block_txs = list(self.pending)

        # 2) Optionally include the mining reward
        if self.enable_reward:
            reward_tx = Transaction(
                tx_type="PAY",
                sender=REWARD_SENDER,
                recipient=miner_addr,
                amount=BLOCK_REWARD,
                fee=0,
                nonce=0,
                signature=REWARD_SIGNATURE,
            )
            block_txs.append(reward_tx)

        # 3) Create the new block header
        last = self.chain[-1]
        blk = Block(
            index=last.index + 1,
            previous_hash=last.hash,
            transactions=block_txs
        )

        # 4) Consensus: PoS or PoW
        if self.use_pos:
            validator = self._select_pos_validator()
            if validator != miner_addr:
                print("not selected in this PoS round")
                return None
            # SLASHING: if this validator already signed this height, burn stake
            last = self._last_signed.get(validator)
            if last == self.chain[-1].index + 1:
                acct = self._get_acct(validator)
                slashed = acct["stake"] // 2
                acct["stake"] -= slashed
                print(f"! Slashed {slashed} from {validator} for double-sign")
            self._last_signed[validator] = self.chain[-1].index + 1
            
            # Lightweight “mining” for PoS
            blk.hash = blk.compute_hash()
            # PoS inflation reward
            self._get_acct(miner_addr)["balance"] += int(BLOCK_REWARD * STAKE_REWARD_PCT)
        else:
            # Heavy work for PoW
            self._mine_pow(blk)

        # 5) Commit state changes and append
        self._apply_block(blk)
        self.pending.clear()
        self.chain.append(blk)
        return blk


    # ---------------------------------------------------------------------#
    #  Block-level state transition
    # ---------------------------------------------------------------------#

    def _apply_block(self, blk: Block):
        for tx in blk.transactions:
            sender = self._get_acct(tx.sender)

            # ------------------ PAY ------------------
            if tx.tx_type == "PAY":
                if tx.sender != "COINBASE":
                    sender["balance"] -= tx.amount + tx.fee
                recipient = self._get_acct(tx.recipient)
                recipient["balance"] += tx.amount

            # ------------------ STAKE / UNSTAKE ------------------
            elif tx.tx_type == "STAKE":
                sender["balance"] -= tx.amount
                sender["stake"] += tx.amount

            elif tx.tx_type == "UNSTAKE":
                sender["stake"] -= tx.amount
                sender["balance"] += tx.amount

            # ------------------ OPEN_REMIT ------------------
            elif tx.tx_type == "OPEN_REMIT":
                rid = tx.payload["id"]
                r_hash = tx.payload["release_hash"]
                self.remits[rid] = Remittance(
                    id=rid,
                    sender=tx.sender,
                    recipient=tx.payload["recipient"],
                    amount=tx.amount,
                    release_hash=r_hash,
                )
                sender["balance"] -= tx.amount + tx.fee

            # ------------------ CLAIM_REMIT ------------------
            elif tx.tx_type == "CLAIM_REMIT":
                rid = tx.payload["id"]
                code = tx.payload["release_code"]

                remit = self.remits.get(rid)
                if remit and not remit.released:
                    if (
                        hashlib.sha256(code.encode()).hexdigest()
                        == remit.release_hash
                    ):
                        recipient = self._get_acct(remit.recipient)
                        recipient["balance"] += remit.amount
                        self.remits[rid] = replace(remit, released=True)

    # ---------------------------------------------------------------------#
    #  Chain validation for new nodes
    # ---------------------------------------------------------------------#

    def is_valid_chain(self) -> bool:
        for i, blk in enumerate(self.chain[1:], 1):
            prev = self.chain[i - 1]
            if blk.previous_hash != prev.hash:
                return False
            if not self.use_pos and not blk.hash.startswith("0" * DIFFICULTY):
                return False
            if blk.hash != blk.compute_hash():
                return False
        return True


# -----------------------------------------------------------------------------#
#  Convenience: simple CLI miner when run directly
# -----------------------------------------------------------------------------#

if __name__ == "__main__":
    from transaction import gen_keypair

    bc = Blockchain()
    priv, pub = gen_keypair()
    bc.accounts[pub] = {"balance": 100_000_000, "nonce": 0, "stake": 0}

    # mine empty (just reward) block
    blk = bc.mine_block(miner_addr=pub)
    if blk:
        print("Mined", blk.hash[:16], "height", blk.index)
        print("Balance: ", bc.accounts[pub]["balance"])
