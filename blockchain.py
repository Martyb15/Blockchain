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
from dataclasses import dataclass, replace
from typing import Dict, List

from block import Block, merkle_root
from config import BLOCK_REWARD, DIFFICULTY, STAKE_REWARD_PCT, REWARD_SENDER, REWARD_SIGNATURE

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
    
    def _is_reward_tx(self, tx: Transaction) -> bool:
        return (
            tx.tx_type == "PAY" 
            and tx.sender == REWARD_SENDER
            and tx.signature == REWARD_SIGNATURE
            )

    def _total_fees(self, tx_list: List[Transaction]) -> int:
        return sum(tx.fee for tx in tx_list if not self._is_reward_tx(tx))
    
    def _validate_payload(self, tx: Transaction) -> bool:
        ''' Validate the payload of remittance transactions. '''
        if tx.tx_type == "PAY":
            return tx.recipient is not None
        elif tx.tx_type == "OPEN_REMIT":
            return (
                isinstance(tx.payload, dict)
                and "id" in tx.payload
                and "recipient" in tx.payload
                and "release_hash" in tx.payload
            )
        elif tx.tx_type == "CLAIM_REMIT":
            return (
                isinstance(tx.payload, dict)
                and "id" in tx.payload
                and "release_code" in tx.payload
            ) 
        return True
    
    def _validate_amount(self, tx: Transaction) -> bool:
        ''' Validate that the amount is positive and within reasonable limits. '''
        if tx.tx_type in {"PAY", "OPEN_REMIT", "STAKE", "UNSTAKE"}:
            return tx.amount > 0 
        return tx.amount <= 0
    
    def _select_pos_validator(self, seed_hex: str, accounts: Dict[str, Dict[str, int]] | None = None) -> str:
        '''   Pick a validator weighted by stake deterministically using a seed, including any pending STAKE txs '''
        accounts = accounts or self.accounts
        stake_entries: list[tuple[str, int]] = [(addr, acct["stake"]) for addr, acct in accounts.items() if acct["stake"] > 0]
        total = sum(s for _, s in stake_entries)
        if total == 0:
            return REWARD_SENDER  # fallback to reward sender if no stake
        r = int(seed_hex, 16) % total
        upto = 0
        for addr, stake in stake_entries:
            upto += stake
            if upto >= r:
                return addr     
        return stake_entries[-1][0]

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


    # def _select_pos_validator(self) -> str:
    #     '''   Pick a validator weighted by stake, including any pending STAKE txs
    # so that newly‐staked tokens count immediately for this round. '''
  
    #     # 1) Build a list of (address, effective_stake)
    #     stake_entries: list[tuple[str, int]] = []
    #     for addr, acct in self.accounts.items():
    #         base_stake = acct["stake"]
    #         # include any pending STAKE txs for this addr
    #         pending_stake = sum(
    #             tx.amount
    #             for tx in self.pending
    #             if tx.tx_type == "STAKE" and tx.sender == addr
    #         )
    #         effective = base_stake + pending_stake
    #         if effective > 0:
    #             stake_entries.append((addr, effective))

    #     # 2) If nobody has any stake, fall back to a random account
    #     total = sum(s for _, s in stake_entries)
    #     if total == 0:
    #         # return random.choice(list(self.accounts) or [""])
    #         return ""

    #     # 3) Choose a random point in [0, total)
    #     r = random.uniform(0, total)
    #     upto = 0
    #     for addr, stake in stake_entries:
    #         upto += stake
    #         if upto >= r:
    #             return addr

    #     # 4) Fallback (shouldn't really happen)
    #     return stake_entries[-1][0]


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

        fees = self._total_fees(block_txs)

        # 2) Optionally include the mining reward
        if self.enable_reward:
            reward_tx = Transaction(
                tx_type="PAY",
                sender=REWARD_SENDER,
                recipient=miner_addr,
                amount=BLOCK_REWARD + fees,
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
        blk.merkle_root = merkle_root([tx.hash() for tx in block_txs])
        seed = hashlib.sha256(f"{last.hash}{blk.merkle_root}".encode()).hexdigest()


        # 4) Consensus: PoS or PoW
        if self.use_pos:
            validator = self._select_pos_validator()
            if not validator:
                print("No eligible PoS validator (no stake)")
                return None
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
                if tx.sender != " REWARD_SENDER":
                    sender["balance"] -= tx.amount + tx.fee
                recipient = self._get_acct(tx.recipient)
                recipient["balance"] += tx.amount

            # ------------------ STAKE / UNSTAKE ------------------
            elif tx.tx_type == "STAKE":
                sender["balance"] -= tx.amount
                sender["stake"] = tx.amount

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
    #  Block validation for incoming blocks
    # ---------------------------------------------------------------------#

    def validate_block(self, blk: Block, prev_blk: Block) -> bool:
        if blk.previous_hash != prev_blk.hash:
            return False
        if blk.index != prev_blk.index + 1:
            return False
        if not self.use_pos and not blk.hash.startswith("0" * DIFFICULTY):
            return False
        
        computed_merkle = merkle_root([tx.hash() for tx in blk.transactions])
        if blk.merkle_root and blk.merkle_root != computed_merkle: 
            return False
        if blk.hash != blk.compute_hash(): 
            return False
        
        reward_txs = [tx for tx in blk.transactions if self._is_reward_tx(tx)]
        if len(reward_txs) > 1: 
            return False
        fees = self._total_fees(blk.transactions)
        if self.enable_reward and reward_txs:
            expected_amount = BLOCK_REWARD + fees
            if reward_txs[0].amount != expected_amount:
                return False
        
        if self.use_pos and reward_txs: 
            seed = hashlib.sha256(f"{prev_blk.hash}{computed_merkle}".encode()).hexdigest()
            validator = self._select_pos_validator(seed, self.accounts)
            if reward_txs[0].recipient != validator:
                return False
            
        temp_accounts = {addr: acct.copy() for addr, acct in self.accounts.items()}
        temp_remits = {rid: remit for rid, remit in self.remits.items()}
        
        def get_temp_acct(addr: str) -> Dict[str, int]:
            return temp_accounts.setdefault(addr, {"balance": 0, "nonce": 0, "stake": 0})
        
        for tx in blk.transactions:
            if not self._is_reward_tx(tx): 
                if not self._validate_payload(tx):
                    return False
                if not self._validate_amount(tx):
                    return False    
                if not tx.verify():
                    return False
                
            sender = get_temp_acct(tx.sender)

            if not self._is_reward_tx(tx):
                if tx.nonce != sender["nonce"] + 1:
                    return False
                sender["nonce"] += 1    

            if tx.tx_type == "PAY":
                if tx.sender != REWARD_SENDER:
                    if sender["balance"] < tx.amount + tx.fee:
                        return False
                    sender["balance"] -= tx.amount + tx.fee
                recipient = get_temp_acct(tx.recipient)
                recipient["balance"] += tx.amount
            
            elif tx.tx_type == "STAKE":
                if sender["balance"] < tx.amount:
                    return False
                sender["balance"] -= tx.amount
                sender["stake"] += tx.amount
            
            elif tx.tx_type == "UNSTAKE":
                if sender["stake"] < tx.amount:
                    return False
                sender["stake"] -= tx.amount
                sender["balance"] += tx.amount  

            elif tx.tx_type == "OPEN_REMIT":
                rid = tx.payload["id"]
                if rid in temp_remits:
                    return False
                temp_remits[rid] = Remittance(
                    id=rid,
                    sender=tx.sender,
                    recipient=tx.payload["recipient"], 
                    amount=tx.amount,
                    release_hash=tx.payload["release_hash"],
                )
                if sender["balance"] < tx.amount + tx.fee: 
                    return False
                sender["balance"] -= tx.amount + tx.fee


            elif tx.tx_type == "CLAIM_REMIT":
                rid = tx.payload["id"]
                code = tx.payload["release_code"]
                remit = temp_remits.get(rid)
                if not remit and not remit.released:
                    if (
                        hashlib.sha256(code.encode()).hexdigest()
                        == remit.release_hash
                    ):
                        return False
                    recipient = get_temp_acct(remit.recipient)
                    recipient["balance"] += remit.amount
                    temp_remits[rid] = replace(remit, released=True)
    
        return True
    # ---------------------------------------------------------------------#
    #  Chain validation for new nodes
    # ---------------------------------------------------------------------#

    def _validate_chain(self, chain: List[Block]) -> bool:
        temp_accounts: Dict[str, Dict[str, int]] = {}
        temp_remits: Dict[str, Remittance] = {}

        def get_temp_acct(addr: str) -> Dict[str, int]:
            return temp_accounts.setdefault(addr, {"balance": 0, "nonce": 0, "stake": 0})
        
        if not chain:
            return False
        genesis = chain[0]
        if genesis.index != 0 or genesis.previous_hash != "0":
            return False
        if genesis.hash != genesis.compute_hash():
            return False
        
        for i, blk in enumerate(chain[1:], 1): 
            prev = chain[i - 1]
            if blk.previous_hash != prev.hash:
                return False
            if not self.use_pos and not blk.hash.startswith("0" * DIFFICULTY):
                return False
            computed_merkle = merkle_root([tx.hash() for tx in blk.transactions])
            if blk.merkle_root and blk.merkle_root != computed_merkle: 
                return False
            if blk.hash != blk.compute_hash():
                return False
            
            reward_txs = [tx for tx in blk.transactions if self._is_reward_tx(tx)]
            if len(reward_txs) > 1:
                return False
            fees = self._total_fees(blk.transactions)
            if self.enable_reward: 
                if not reward_txs:
                    return False
                if reward_txs[0].amount != BLOCK_REWARD + fees:
                    return False
            
            if self.use_pos and reward_txs:
                merkle_root = blk.merkle_root or merkle_root([tx.hash() for tx in blk.transactions])
                seed = hashlib.sha256(f"{prev.hash}{merkle_root}".encode()).hexdigest()
                validator = self._select_pos_validator(seed, temp_accounts)
                if reward_txs[0].recipient != validator:
                    return False

            for tx in blk.transactions: 
                if not self._is_reward_tx(tx):
                    if not self._validate_payload(tx):
                        return False
                    if not self._validate_amount(tx):
                        return False
                    if not tx.verify():
                        return False

                sender = get_temp_acct(tx.sender)

                if not self._is_reward_tx(tx):
                    if tx.nonce != sender["nonce"] + 1:
                        return False
                    sender["nonce"] += 1

                if tx.tx_type == "PAY":
                    if tx.sender != REWARD_SENDER:
                        if sender["balance"] < tx.amount + tx.fee:
                            return False
                        sender["balance"] -= tx.amount + tx.fee
                    recipient = get_temp_acct(tx.recipient)
                    recipient["balance"] += tx.amount

                elif tx.tx_type == "STAKE":
                    if sender["balance"] < tx.amount:
                        return False
                    sender["balance"] -= tx.amount
                    sender["stake"] += tx.amount

                elif tx.tx_type == "UNSTAKE":
                    if sender["stake"] < tx.amount:
                        return False
                    sender["stake"] -= tx.amount
                    sender["balance"] += tx.amount

                elif tx.tx_type == "OPEN_REMIT":
                    rid = tx.payload["id"]
                    if rid in temp_remits:
                        return False
                    temp_remits[rid] = Remittance(
                        id=rid,
                        sender=tx.sender,
                        recipient=tx.payload["recipient"],
                        amount=tx.amount,
                        release_hash=tx.payload["release_hash"],
                    )
                    if sender["balance"] < tx.amount + tx.fee:
                        return False
                    sender["balance"] -= tx.amount + tx.fee

                elif tx.tx_type == "CLAIM_REMIT":
                    rid = tx.payload["id"]
                    code = tx.payload["release_code"]
                    remit = temp_remits.get(rid)
                    if remit and not remit.released:
                        if (
                            hashlib.sha256(code.encode()).hexdigest()
                            == remit.release_hash
                        ):
                            recipient = get_temp_acct(remit.recipient)
                            recipient["balance"] += remit.amount
                            temp_remits[rid] = replace(remit, released=True)    
        return True

    def is_valid_chain(self) -> bool:
        return self._validate_chain(self.chain)
    
    def replace_chain(self, new_chain: List[Block]) -> bool:
        if len(new_chain) <= len(self.chain):
            return False
        if not self._validate_chain(new_chain): 
            return False
        self.chain = new_chain
        self.accounts = {}
        self.remits = {}
        self.pending = []
        self._last_signed = {}
        for blk in self.chain[:1]: 
            self._apply_block(blk)
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
