# Mini Blockchain (Python)

A small educational blockchain implementation in Python with: 
- Proof-of-Work mining (leading-zero difficulty)
- Optional Proof-of-Stake validator selection + basic slashing behavior
- ECDSA (secp256k1) transaction signing/verification
- Merkle root over transactoin hashes
- Simple remittance escrow flow (OPEN_REMIT / CLAIM_REMIT)
- FastAPI HTTP API for interacting with the chain
- Minimal WebSocket P2P demo node (broadcast tx + blocks)
- Pytest test suite



### Quickstart
    py -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -U pip
    pip install -r requirements-dev.txt
    python -m pytest -q
    python -m uvicorn api:app --reload --port 5000