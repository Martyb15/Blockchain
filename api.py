# api.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

from blockchain import Blockchain
from transaction import Transaction

# Instantiate one shared chain (in-memory)
chain = Blockchain(use_pos=False, enable_reward=True)
app = FastAPI()

# Pydantic models for request bodies
class FaucetReq(BaseModel):
    address: str
    amount: int = 50_000_000

class TxReq(BaseModel):
    tx_type: str
    sender: str
    recipient: Optional[str]
    amount: int
    fee: int
    nonce: int
    payload: Optional[dict]
    signature: Optional[str] = None

# --- Endpoints ---

@app.post("/faucet")
def faucet(req: FaucetReq):
    chain.accounts[req.address] = {"balance": req.amount, "nonce": 0, "stake": 0}
    return {"status": "ok", "funded": req.address, "amount": req.amount}

@app.post("/tx")
def send_tx(req: TxReq):
    # Build the TX object (no signature yet)
    tx = Transaction(
        tx_type=req.tx_type,
        sender=req.sender,
        recipient=req.recipient,
        amount=req.amount,
        fee=req.fee,
        nonce=req.nonce,
        payload=req.payload,
        signature=None,
    )

    # If client passed us a PEM‐encoded private key, sign with it
    if req.signature and req.signature.startswith("-----BEGIN"):
        tx.sign(req.signature)
    else:
        # Otherwise, assume they passed a real signature hex
        tx.signature = req.signature

    # Now try to enqueue
    added = chain.add_tx(tx)
    if not added:
        raise HTTPException(status_code=400, detail="Transaction rejected")

    return {"status": "pending", "tx_hash": tx.hash()}

@app.post("/mine")
def mine(miner: str):
    blk = chain.mine_block(miner_addr=miner)
    if blk is None:
        raise HTTPException(status_code=400, detail="Nothing to mine or not validator")
    return {"status": "mined", "block": blk.compute_hash(), "height": blk.index}

@app.get("/balance/{addr}")
def balance(addr: str):
    acct = chain.accounts.get(addr)
    if acct is None:
        return {"address": addr, "balance": 0}
    return {"address": addr, "balance": acct["balance"], "stake": acct["stake"]}

@app.get("/block/{height}")
def get_block(height: int):
    if height < 0 or height >= len(chain.chain):
        raise HTTPException(status_code=404, detail="Block not found")
    blk = chain.chain[height]
    return {
        "index": blk.index,
        "prev": blk.previous_hash,
        "timestamp": blk.timestamp,
        "transactions": [tx.hash() for tx in blk.transactions],
        "nonce": blk.nonce,
        "hash": blk.hash,
    }

@app.get("/chain")
def get_chain() -> List[str]:
    return [blk.hash for blk in chain.chain]

# --- Run via: uvicorn api:app --reload --port 5000 ---  
if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=5000, reload=True)
