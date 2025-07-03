# test_remittance.py

import secrets
import hashlib
import pytest

from blockchain import Blockchain
from transaction import Transaction, gen_keypair

def test_remit_roundtrip():
    # 1) Setup a fresh chain and two wallets
    bc = Blockchain()
    privA, pubA = gen_keypair()
    privB, pubB = gen_keypair()

    # Give Alice some funds to start
    bc.accounts[pubA] = {"balance": 10_000_000, "nonce": 0, "stake": 0}

    # 2) Prepare an escrow (OPEN_REMIT)
    code = "secret123"
    rhash = hashlib.sha256(code.encode()).hexdigest()
    rid = secrets.token_hex(8)

    open_tx = Transaction(
        tx_type="OPEN_REMIT",
        sender=pubA,
        recipient=None,
        amount=5_000_000,
        fee=1_000,
        nonce=1,
        payload={"id": rid, "recipient": pubB, "release_hash": rhash},
    )
    open_tx.sign(privA)
    assert bc.add_tx(open_tx), "OPEN_REMIT should be accepted"

    # Mine the open-escrow transaction
    bc.mine_block(miner_addr=pubA)

    # 3) Claim the escrow (CLAIM_REMIT)
    claim_tx = Transaction(
        tx_type="CLAIM_REMIT",
        sender=pubB,
        recipient=None,
        amount=0,
        fee=0,
        nonce=1,
        payload={"id": rid, "release_code": code},
    )
    claim_tx.sign(privB)
    assert bc.add_tx(claim_tx), "CLAIM_REMIT should be accepted"

    # Mine the claim transaction
    bc.mine_block(miner_addr=pubB)

    # 4) Verify Bob received the funds and the contract is marked released
    assert bc.accounts[pubB]["balance"] == 5_000_000
    assert bc.remits[rid].released is True
