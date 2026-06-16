import copy
import hashlib
import secrets

from src.pychain.blockchain import Blockchain
from src.pychain.transaction import Transaction, gen_keypair
from src.pychain.config import BLOCK_REWARD


def _signed_pay(priv, sender, recipient, amount, nonce, fee=0):
    tx = Transaction("PAY", sender, recipient, amount, fee, nonce)
    tx.sign(priv)
    return tx


def build_remit_chain():
    """Mine a reward-funded PoW chain that opens and then claims an escrow.

    Every spend is covered by on-chain mining rewards, so the resulting chain
    is self-consistent when replayed from genesis (no off-chain faucet funds).
    """
    bc = Blockchain(use_pos=False, enable_reward=True)
    priv, pub = gen_keypair()
    privB, pubB = gen_keypair()
    code = "open-sesame"
    rhash = hashlib.sha256(code.encode()).hexdigest()
    rid = secrets.token_hex(8)

    # Block 1: a zero-value self-payment so there's something to mine; the
    # miner reward funds `pub` on-chain.
    assert bc.add_tx(_signed_pay(priv, pub, pub, 0, nonce=1))
    assert bc.mine_block(miner_addr=pub)

    # Block 2: open a 5M escrow for pubB.
    open_tx = Transaction(
        "OPEN_REMIT", pub, None, 5_000_000, 0, 2,
        payload={"id": rid, "recipient": pubB, "release_hash": rhash},
    )
    open_tx.sign(priv)
    assert bc.add_tx(open_tx)
    assert bc.mine_block(miner_addr=pub)

    # Block 3: pubB claims the escrow by revealing the preimage.
    claim_tx = Transaction(
        "CLAIM_REMIT", pubB, None, 0, 0, 1,
        payload={"id": rid, "release_code": code},
    )
    claim_tx.sign(privB)
    assert bc.add_tx(claim_tx)
    assert bc.mine_block(miner_addr=pub)

    return bc, pub, pubB, rid


def test_mined_chain_validates_from_genesis():
    bc, *_ = build_remit_chain()
    assert bc.is_valid_chain()


def test_replace_chain_replays_remittance():
    bc, pub, pubB, rid = build_remit_chain()
    fresh = Blockchain(use_pos=False, enable_reward=True)
    assert fresh.replace_chain(list(bc.chain))

    # The escrow credited pubB and is marked released after replay.
    assert fresh.accounts[pubB]["balance"] == 5_000_000
    assert fresh.remits[rid].released is True
    # Three reward blocks credited the miner; the escrow debited 5M.
    assert fresh.accounts[pub]["balance"] == 3 * BLOCK_REWARD - 5_000_000


def test_replace_chain_rejects_shorter_or_equal():
    bc, *_ = build_remit_chain()
    fresh = Blockchain(use_pos=False, enable_reward=True)
    # A chain no longer than the current one is never adopted.
    assert fresh.replace_chain([bc.chain[0]]) is False


def test_validate_block_accepts_genuine_and_rejects_tampered():
    bc, *_ = build_remit_chain()
    fresh = Blockchain(use_pos=False, enable_reward=True)
    genesis, block1 = bc.chain[0], bc.chain[1]

    assert fresh.validate_block(block1, genesis) is True

    # Mutating the transaction list invalidates the stored hash/merkle root.
    tampered = copy.deepcopy(block1)
    tampered.transactions.append(tampered.transactions[0])
    assert fresh.validate_block(tampered, genesis) is False
