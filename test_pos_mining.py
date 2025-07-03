import pytest

from blockchain import Blockchain
from transaction import Transaction, gen_keypair
from config import BLOCK_REWARD, STAKE_REWARD_PCT

def test_pos_mining_rewards_and_selection_single_staker():
    # PoS mode, no standard mining reward (enable_reward=False)
    bc = Blockchain(use_pos=True, enable_reward=False)
    priv, pub = gen_keypair()

    # Seed account with 100M units
    bc.accounts[pub] = {"balance": 100_000_000, "nonce": 0, "stake": 0}

    # Step 1: STAKE half the funds (50M)
    stake_amount = 50_000_000
    stake_tx = Transaction(
        tx_type="STAKE",
        sender=pub,
        recipient=None,
        amount=stake_amount,
        fee=0,
        nonce=1,
    )
    stake_tx.sign(priv)
    assert bc.add_tx(stake_tx), "STAKE tx should be accepted"
    blk1 = bc.mine_block(miner_addr=pub)
    assert blk1 is not None, "Staker must be allowed to mine PoS block"

    # After mining: stake recorded and inflation applied
    assert bc.accounts[pub]["stake"] == stake_amount
    expected_balance = 100_000_000 - stake_amount + int(BLOCK_REWARD * STAKE_REWARD_PCT)
    assert bc.accounts[pub]["balance"] == expected_balance

def test_pos_mining_fails_for_non_validator():
    # PoS mode, no standard reward
    bc = Blockchain(use_pos=True, enable_reward=False)
    privA, pubA = gen_keypair()
    privB, pubB = gen_keypair()

    # Both get initial balances, but only A stakes
    bc.accounts[pubA] = {"balance": 100_000_000, "nonce": 0, "stake": 0}
    bc.accounts[pubB] = {"balance": 100_000_000, "nonce": 0, "stake": 0}

    # A stakes 10M
    stake_tx = Transaction(
        tx_type="STAKE",
        sender=pubA,
        recipient=None,
        amount=10_000_000,
        fee=0,
        nonce=1,
    )
    stake_tx.sign(privA)
    assert bc.add_tx(stake_tx)
    blk1 = bc.mine_block(miner_addr=pubA)
    assert blk1 is not None

    # B tries to mine a simple PAY tx without stake
    pay_tx = Transaction(
        tx_type="PAY",
        sender=pubA,
        recipient=pubB,
        amount=1_000_000,
        fee=0,
        nonce=bc.accounts[pubA]["nonce"] + 1,
    )
    pay_tx.sign(privA)
    assert bc.add_tx(pay_tx)

    blk2 = bc.mine_block(miner_addr=pubB)
    assert blk2 is None, "Non-validator must not be allowed to mine in PoS mode"
