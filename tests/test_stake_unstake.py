import hashlib
import secrets

import pytest

from src.pychain.blockchain import Blockchain
from src.pychain.transaction import Transaction, gen_keypair

def test_stake_and_unstake_roundtrip():
    # 1) Fresh chain + one wallet
    bc = Blockchain(use_pos=False, enable_reward=False)
    priv, pub = gen_keypair()

    # Seed the account with 100M units
    bc.accounts[pub] = {"balance": 100_000_000, "nonce": 0, "stake": 0}

    # 2) STAKE: lock up 10M
    stake_tx = Transaction(
        tx_type="STAKE",
        sender=pub,
        recipient=None,
        amount=10_000_000,
        fee=0,
        nonce=1,
    )
    stake_tx.sign(priv)
    assert bc.add_tx(stake_tx), "STAKE tx should be accepted"
    bc.mine_block(miner_addr=pub)

    # After staking: balance down, stake up
    assert bc.accounts[pub]["balance"] == 90_000_000
    assert bc.accounts[pub]["stake"]   == 10_000_000

    # 3) UNSTAKE: release 7M back
    unstake_tx = Transaction(
        tx_type="UNSTAKE",
        sender=pub,
        recipient=None,
        amount=7_000_000,
        fee=0,
        nonce=2,
    )
    unstake_tx.sign(priv)
    assert bc.add_tx(unstake_tx), "UNSTAKE tx should be accepted"
    bc.mine_block(miner_addr=pub)

    # After unstaking: stake down, balance up
    assert bc.accounts[pub]["stake"]   == 3_000_000
    assert bc.accounts[pub]["balance"] == 97_000_000
