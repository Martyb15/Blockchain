from blockchain import Blockchain
from transaction import Transaction, gen_keypair

# ---- wallets ----
privA, pubA = gen_keypair()
privB, pubB = gen_keypair()
bc = Blockchain(use_pos=False, enable_reward=True)
# fund Alice from nowhere (demo only!)
bc.accounts[pubA] = {"balance": 100_000_000, "nonce": 0, "stake": 0}

# ---- normal tx ----
tx = Transaction(
    tx_type="PAY",
    sender=pubA,
    recipient=pubB,
    amount=25_000_000,
    fee=1_000_000,
    nonce=1,
)
tx.sign(privA)
bc.add_tx(tx)

# ---- mine ----
blk = bc.mine_block(miner_addr=pubA)
print("Mined block", blk.hash[:16], "height", blk.index)
print("Balances ⇒", bc.accounts[pubA]["balance"], "/", bc.accounts[pubB]["balance"])
