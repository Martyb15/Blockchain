# send_tx.py

import asyncio
import json
import websockets
from transaction import Transaction, gen_keypair

async def main():
    # 1) Generate a fresh wallet for this demo
    priv, pub = gen_keypair()
    print(f"🔑  New demo wallet:\n  PUB (fund this on each node):\n  {pub}\n")

    # 👉 BEFORE running this script, in each P2P node’s REPL do:
    #    node.blockchain.accounts[pub] = {"balance": 50_000_000, "nonce": 0, "stake": 0}

    # 2) Build & sign a trivial TX (sending to self for simplicity)
    tx = Transaction(
        tx_type="PAY",
        sender=pub,
        recipient=pub,
        amount=1_000_000,
        fee=0,
        nonce=1,
    )
    tx.sign(priv)

    # 3) Broadcast it to Node A (ws://localhost:8000)
    msg = json.dumps({"type": "tx", "payload": tx.to_dict()})
    async with websockets.connect("ws://localhost:8000") as ws:
        await ws.send(msg)
        print("✅ Transaction broadcast to ws://localhost:8000")

if __name__ == "__main__":
    asyncio.run(main())
