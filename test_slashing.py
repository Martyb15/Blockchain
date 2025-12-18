import pytest
from blockchain import Blockchain
from transaction import Transaction, gen_keypair

def test_double_signing_is_slashed():
    bc = Blockchain(use_pos=True, enable_reward=False)
    priv, pub = gen_keypair()
    # Seed and stake
    bc.accounts[pub] = {"balance": 100_000_000, "nonce": 0, "stake": 0}
    stake_tx = Transaction("STAKE", pub, None, 20_000_000, 0, 1)
    stake_tx.sign(priv)
    bc.add_tx(stake_tx)
    blk1 = bc.mine_block(miner_addr=pub)
    assert blk1 is not None

    # Simulate two competing blocks at the same height:
    # Force-block A
    bc.pending.clear()
    fake_blkA = Transaction("PAY", pub, pub, 0, 0, bc.accounts[pub]["nonce"]+1)
    fake_blkA.sign(priv)
    bc.add_tx(fake_blkA)
    bc.chain.pop()  # remove last real block to reuse height
    blkA = bc.mine_block(miner_addr=pub)
    assert blkA is not None

    # Force-block B (same height) – you resign another block
    bc.pending.clear()
    fake_blkB = Transaction("PAY", pub, pub, 0, 0, bc.accounts[pub]["nonce"]+1)
    fake_blkB.sign(priv)
    bc.add_tx(fake_blkB)
    # Now mining again at same height should trigger slashing
    blkB = bc.mine_block(miner_addr=pub)
    assert blkB is not None

    # After double-sign, half their stake is gone
    remaining = bc.accounts[pub]["stake"]
    assert remaining == 10_000_000, f"Expected stake to be halved, got {remaining}"
