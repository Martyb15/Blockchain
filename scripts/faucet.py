# faucet.py

import sys
import asyncio
import json
import websockets

async def main():
    if len(sys.argv) < 2:
        print("Usage: python faucet.py <PUBKEY> [amount]")
        return

    address = sys.argv[1]
    amount  = int(sys.argv[2]) if len(sys.argv) > 2 else 50_000_000  # no second arguement... default 50,000,000 to given pubkey

    msg = json.dumps({
        "type": "faucet",
        "payload": {
            "address": address,
            "amount": amount
        }
    })

    async with websockets.connect("ws://localhost:8000") as ws:
        await ws.send(msg)
        print(f"Requested {amount} units to {address} via faucet")

if __name__ == "__main__":
    asyncio.run(main())
