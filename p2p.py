# p2p.py

import asyncio
import json
import argparse
import websockets

from blockchain import Blockchain
from block import Block
from transaction import Transaction, gen_keypair

""" Without P2P we are left with a single Blockchain object on one machine = just a database with extra steps.
    With P2P, each node has its own Blockchain instance, and they communicate over websockets to share transactions and blocks.
    This is a minimal P2P implementation for demo purposes only.
"""

class P2PNode:
    def __init__(self, port: int, peers: list[str]):
        self.port = port
        self.peers = peers
        self.blockchain = Blockchain(use_pos=False, enable_reward=True)

        # Generate and fund this node’s own wallet
        self.priv_key, self.miner_addr = gen_keypair()
        self.blockchain.accounts[self.miner_addr] = {
            "balance": 100_000_000,
            "nonce": 0,
            "stake": 0,
        }

    async def handler(self, ws, path=None):
        """ Handle incoming messages from peers (listens on self.port for messages) """
        async for msg in ws:
            data = json.loads(msg)
            kind = data.get("type")

            if kind == "faucet":
                # Faucet: credit an address directly
                addr = data["payload"]["address"]
                amt  = data["payload"].get("amount", 50_000_000)
                self.blockchain.accounts[addr] = {"balance": amt, "nonce": 0, "stake": 0}
                print(f"[Node {self.port}] Faucet funded {addr} with {amt}")


            elif kind == "tx":
                # Recieves a transaction, validates it and adds to mempool
                tx = Transaction.from_dict(data["payload"])
                added = self.blockchain.add_tx(tx)
                print(f"[Node {self.port}] Received TX: added={added}")
                if added:
                    asyncio.create_task(self.broadcast("tx", tx.to_dict()))

            elif kind == "block":
                # Recieves a new block(mined by a peer), validates and appends to local chain
                blk = Block.from_dict(data["payload"])
                if (self.blockchain.is_valid_chain() and blk.index == self.blockchain.chain[-1].index + 1):
                    self.blockchain._apply_block(blk)
                    self.blockchain.chain.append(blk)
                    print(f"[Node {self.port}] Appended block {blk.index}")
                else:
                    print(f"[Node {self.port}] Rejected block {blk.index}")
            else:
                print(f"[Node {self.port}] Unknown message: {data}")


    async def broadcast(self, kind: str, obj: dict):
        """ Broadcast a message to all peers
            When this node mines a block or receives a valid tx, it broadcasts to peers
        
            kind: 'tx', 'block', 'faucet'
            obj: dict payload
         """
        msg = json.dumps({"type": kind, "payload": obj})
        for peer in self.peers:
            try:
                async with websockets.connect(peer) as ws:
                    await ws.send(msg)
            except Exception as e:
                print(f"[Node {self.port}] Failed to send to {peer}: {e}")


    async def periodic_mine(self):
        """ Periodically attempt to mine a block every 5 seconds """
        while True:
            await asyncio.sleep(5)
            blk = self.blockchain.mine_block(miner_addr=self.miner_addr)
            if blk:
                print(f"[Node {self.port}] Mined block {blk.index}")
                await self.broadcast("block", blk.to_dict())


    async def run(self):
        server = await websockets.serve(self.handler, "localhost", self.port)
        print(f"[Node {self.port}] Listening on ws://localhost:{self.port}")
        asyncio.create_task(self.periodic_mine())
        await server.wait_closed()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument(
        "--peers",
        nargs="*",
        default=[],
        help="List of ws://host:port of other nodes",
    )
    args = parser.parse_args()
    node = P2PNode(port=args.port, peers=args.peers)
    asyncio.run(node.run())



# ==== How to run: ==== # 
# 1) Start multiple nodes in separate terminals:
#    python p2p.py --port 8000 --peers ws://localhost:8001
#    python p2p.py --port 8001 --peers ws://localhost:8000
# 2) In each node’s REPL, fund the demo wallet address printed on startup:
#    node.blockchain.accounts["demo_wallet_pub_key"] = {"balance": 50_000_000, "nonce": 0, "stake": 0}
# 3) Run send_tx.py to broadcast a transaction to one node: 
