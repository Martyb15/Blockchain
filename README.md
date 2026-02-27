# Mini Blockchain (Python)

A blockchain in Python exploring consensus mechanisms and cryptographic signing. 
- Proof-of-Work mining (leading-zero difficulty)
- Proof-of-Stake Validator selection with slashing
- ECDSA (secp256k1) transaction signing/verification
- Merkle root over transaction hashes
- Hash-locked remittance escrow flow (OPEN_REMIT / CLAIM_REMIT)
- FastAPI REST API + Swagger docs
- WebSocket P2P demo node (broadcast tx + blocks)
- React frontend for wallet operations
- Pytest test suite

> Portfolio/learning project.

---

## Local Quickstart (Windows)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
python -m pytest -q
python -m uvicorn pychain.api:app --reload --port 5000

Docker
docker build -t pychain . 
docker run -p 5000:5000 pychain
```

## API Endpoints
| Method | Endpoint | Description | 
|--------|----------|-------------|
| POST   | /faucet |Fund an address (testing only)|
| POST   | /tx |Submit a signed transaction|
| POST   | /mine|Mine a new block (PoW)|
| POST   | /stake |Stake coins to become a validator|
| POST   | /unstake |Withdraw staked coins|
| POST   | /open_remit|Create a hash-locked escrow|
| POST   | /claim_remit|Claim escrow by revealing the secret|
| GET   | /balance/{addr}|Check address balance and nonce|
| GET   | /chain |Return the full chain (block hashes)|


## Transaction Types
| Type | Purpose |
|------|---------|
|PAY|Transfer coins between addresses|
|STAKE|Lock coins to participate in PoS validation|
|UNSTAKE|Unlock previously staked coins|
|OPEN_REMIT|Lock funds in escrow with a hash condition|
|CLAIM_REMIT|Release escrowed funds by providing preimage|


## Design Decisions
- Dual consensus: PoW and PoS are both implemented to understand the tradeoffs, PoW is reate-limited by mining difficulty, PoS by cryptographic operations and validator selection. 
- Five transactoin types: Rather than building a single PAY flow, the system models staking, escrow, and penalties to explore how real blockchains handle economic incentives. 
- Deterministic hashing: Blocks and transactions use canonical serialization to ensure hash stability across nodes. 
- Nonce-based replay protection: Each transaction includes a sender nonce to prevent replay attacks. 
- In-memory state: State lives in memory rather than a database, a deliberate simplification to keep the focus on blockchain mechanics rather than presistence infrastructure. 