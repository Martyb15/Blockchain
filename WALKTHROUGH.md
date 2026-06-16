# PyChain — Project Walkthrough & Interview Guide

A guide to explaining this project confidently. It covers the **30-second pitch**,
the **architecture**, the **transaction lifecycle**, the **consensus mechanisms**,
the **refactor story**, **honest limitations**, and **anticipated interview Q&A**.

---

## 1. The 30-second pitch

> "PyChain is a from-scratch blockchain in Python that implements the core
> mechanics of a real cryptocurrency: ECDSA-signed transactions, a Merkle-committed
> block structure, **two pluggable consensus algorithms** (Proof-of-Work and
> Proof-of-Stake with slashing), and a small set of 'smart-contract-like'
> transaction types — including a **hash-locked escrow** for cross-border
> remittances. It exposes a FastAPI REST API and a minimal WebSocket P2P node, and
> it's covered by a pytest suite. The state machine is deliberately built around a
> **single source of truth** so that mining, block validation, and full-chain
> validation can never disagree."

Lead with that. Then let them pull on whichever thread interests them.

---

## 2. Architecture at a glance

```
src/pychain/
├── config.py        # Tunable constants (difficulty, reward, JSON serialization)
├── transaction.py   # Transaction dataclass + ECDSA keygen / sign / verify
├── block.py         # Block dataclass + Merkle root
├── blockchain.py    # ★ The ledger + consensus engine (the heart of the project)
├── wallet.py        # Key/address helper
├── api.py           # FastAPI REST layer (in-memory shared chain)
└── p2p.py           # WebSocket peer node (broadcast txs/blocks, sync chains)

tests/               # pytest: remittance, stake/unstake, PoS, slashing, chain validation
blockchain-ui/       # React frontend (wallet operations)
scripts/             # Demo CLIs (main, faucet, send_tx)
```

**One sentence per module** (good for a whiteboard):
- `config` — knobs.
- `transaction` — *what* moves value and *how it's authenticated*.
- `block` — *how transactions are batched and committed*.
- `blockchain` — *the rules*: mempool, consensus, state transitions, validation.
- `api` / `p2p` — two different *front doors* to the same engine.

---

## 3. Core data model

### Account state (the "world state")
The chain is **account-based** (like Ethereum), not UTXO-based (like Bitcoin):

```python
accounts: dict[str, {"balance": int, "nonce": int, "stake": int}]
remits:   dict[str, Remittance]   # open/closed escrow contracts
```

- The **account key is the public key** (uncompressed secp256k1 point, hex). The
  sender field of a transaction *is* the public key, which is exactly what's needed
  to verify its signature.
- `balance` is in the smallest unit ("satoshis").
- `nonce` is the per-account counter that gives **replay protection**.
- `stake` is locked collateral for Proof-of-Stake.

### Transaction (`transaction.py`)
A frozen dataclass with six types: `PAY`, `STAKE`, `UNSTAKE`, `OPEN_REMIT`,
`CLAIM_REMIT`, `SLASH`.

Two details worth highlighting:
1. **Deterministic hashing.** `_body()` serializes the tx with
   `json.dumps(..., sort_keys=True, separators=(",", ":"))` — sorted keys, no
   whitespace — so the byte representation (and therefore the hash and signature)
   is identical on every machine. **The signature field is excluded** from the body
   (you can't sign your own signature).
2. **ECDSA over secp256k1.** `sign()` signs the body with a PEM private key;
   `verify()` reconstructs the public key from `sender` and checks the signature.
   Same curve Bitcoin/Ethereum use.

### Block (`block.py`)
```python
index, previous_hash, timestamp, transactions, nonce, merkle_root, hash
```
The block hash commits to `{index, previous_hash, timestamp, nonce, merkle_root}`.
Note it does **not** hash the full transaction list directly — it hashes the
**Merkle root** of the transaction hashes. That's the whole point of a Merkle tree:
a single 32-byte root cryptographically commits to every transaction, so tampering
with any tx changes the root, which changes the block hash, which breaks the chain.

---

## 4. The transaction lifecycle (the spine of the demo)

This is the story to walk an interviewer through end-to-end:

```
1. CREATE   Transaction(tx_type="PAY", sender=pubA, recipient=pubB, amount, fee, nonce)
2. SIGN     tx.sign(privA)          → attaches ECDSA signature over the canonical body
3. SUBMIT   chain.add_tx(tx)        → mempool admission checks (see below)
4. MINE     chain.mine_block(miner) → consensus runs, state applied, block appended
5. VALIDATE peers run validate_block / _validate_chain before accepting
```

**`add_tx` — the mempool gate.** Before a tx ever reaches a block it must pass:
allow-listed type → valid payload shape → sane amount → **valid signature** →
**correct nonce** (`tx.nonce == account.nonce + 1`) → **sufficient funds/stake**.
Only then is it enqueued and the account's nonce advanced.

**`mine_block` — assemble + consensus + commit.**
1. Snapshot the mempool into `block_txs`.
2. If rewards are enabled, append a synthetic **coinbase** tx: a `PAY` from the
   special `SYSTEM` sender (signature `"GENESIS"`) paying `BLOCK_REWARD + fees` to
   the miner. `_is_reward_tx()` recognizes it and exempts it from signature/nonce/
   balance checks.
3. Build the block, compute its Merkle root.
4. Run **consensus** (PoW or PoS — section 5).
5. `_apply_block()` commits every tx to live state, clear the mempool, append.

---

## 5. Consensus: one engine, two algorithms

The constructor flag `use_pos` switches the algorithm. This is a great talking
point — it shows you understand the *tradeoff*, not just one mechanism.

### Proof-of-Work (default)
`_mine_pow` brute-forces the block `nonce` until the hash has `DIFFICULTY` leading
zeros. Security comes from **burning electricity**: rewriting history means redoing
all that work. Rate-limited by computation.

### Proof-of-Stake (`use_pos=True`)
- **Validator selection is deterministic and stake-weighted.** Seed =
  `sha256(previous_block_hash)`; reduce it modulo total stake; walk the staked
  accounts accumulating stake until you pass the seed point. More stake → higher
  selection probability. No electricity burned.
- The selected validator **must equal the miner** or the block is rejected
  (`"not selected in this PoS round"`).
- Reward is **inflationary**: `BLOCK_REWARD * STAKE_REWARD_PCT` (2%).

### Slashing (the PoS security model)
Slashing punishes validators who misbehave by **burning half their stake**. Two paths:
1. **In-protocol double-sign detection** while mining: `_last_signed` remembers the
   last height each validator signed; signing the same height twice halves stake.
2. **`SLASH` transaction with cryptographic evidence**: anyone can submit two
   competing blocks (`block_a`, `block_b`) that share a parent but differ, both
   naming the offender as the selected validator. `_valid_slash_evidence` verifies
   the evidence before the penalty applies. This is how real PoS chains
   (e.g. Ethereum) turn "I saw you cheat" into an on-chain, verifiable penalty.

> Interview soundbite: *"PoW makes attacks expensive in energy; PoS makes them
> expensive in capital — and slashing is what makes that capital actually at risk."*

---

## 6. The validation architecture — my favorite design point

This is the part to be proud of after the refactor. A blockchain has to apply
transactions in **three** situations:

| Situation              | Method            | Trust level                |
|------------------------|-------------------|----------------------------|
| Committing a mined block | `_apply_block`  | Trusted (already validated)|
| A peer sends one block | `validate_block`  | Untrusted — verify everything |
| Bootstrapping/replacing a whole chain | `_validate_chain` | Untrusted — verify from genesis |

The naive way (and how this project *originally* worked) is to **copy-paste the
per-transaction state machine into all three** — ~300 lines, three times. That
duplication had already **drifted into real bugs** (see section 7).

**The fix: a single source of truth.**
```python
_apply_tx(tx, accounts, remits, *, validate: bool)
```
- `validate=False` → trust the tx and apply its effect (used when committing
  blocks that already passed consensus).
- `validate=True` → enforce **every** rule (signature, nonce, funds, payload,
  amount, slash evidence) and bail on the first violation.

Plus `_check_block()` for the structural/consensus header checks (link to parent,
PoW difficulty, Merkle integrity, reward correctness, PoS validator match).

Now all three call sites are 3–15 lines that delegate to the same core. **They
can't disagree, because there's only one implementation.**

```python
def validate_block(self, blk, prev_blk):
    if not self._check_block(blk, prev_blk, self.accounts):
        return False
    accounts = {a: acct.copy() for a, acct in self.accounts.items()}  # work on a copy
    remits = dict(self.remits)
    return all(self._apply_tx(tx, accounts, remits, validate=True)
               for tx in blk.transactions)
```

> Interview soundbite: *"I noticed the validation logic was duplicated three times
> and had silently diverged into bugs. I collapsed it into one parameterized state
> transition. DRY here isn't cosmetic — divergent copies of consensus rules are how
> chains fork by accident."*

**Chain selection** (`replace_chain`) follows the **longest-valid-chain rule**:
adopt an incoming chain only if it's strictly longer *and* fully valid from genesis.

---

## 7. The refactor story (what I improved)

Great to volunteer — it shows you can read, critique, and harden existing code.

**Simplification**
- `blockchain.py`: **691 → 522 lines.** Three near-identical transaction state
  machines collapsed into one `_apply_tx` + one `_check_block`.
- Deleted dead code (a large commented-out function, a stale TODO tracker).

**Bugs found and fixed (most were *hidden inside* the duplication):**
- **Inverted escrow check** — block validation rejected a *correct* secret and
  credited an *incorrect* one (the comparison was backwards in one of the three copies).
- **Inconsistent PoS seed** — `validate_block` derived the validator from a
  different seed than the miner used, so it would reject legitimately-produced blocks.
- **Broken slash evidence** — compared a block *index* (int) to a *hash* (str), so
  it was always false.
- **`Wallet.generate()` crashed** on every call (typos: `gen_keypari`, mismatched
  variable names).
- **`merkle_root` mutated its caller's list** (aliasing bug).
- **P2P** used `self.blockchain[-1]` (not subscriptable) instead of `.chain[-1]`.

**Hygiene**
- Untracked ~6,700 accidentally-committed files (a whole Windows `.venv/`,
  build artifacts) that were already in `.gitignore`.

**Tests**
- Added coverage for the previously-**untested** validation paths
  (`is_valid_chain`, `replace_chain`, `validate_block`), including the fixed
  escrow flow. Suite went 5 → **9 passing**.

---

## 8. Security properties (be ready to enumerate these)

- **Authenticity** — every non-coinbase tx carries an ECDSA signature verified
  against the sender's public key. You can't spend from an account you don't own.
- **Replay protection** — strictly increasing per-account nonces; a captured tx
  can't be re-broadcast.
- **Integrity** — Merkle root + block-hash chaining means any tampering with a past
  transaction invalidates every block after it.
- **Determinism** — canonical JSON serialization ⇒ identical hashes across nodes,
  so independent nodes agree on what a block *is*.
- **Economic security** — PoW (energy cost) or PoS + slashing (capital at risk).

---

## 9. Honest limitations & "what I'd do next"

Interviewers respect candidates who know the edges of their own work.

- **In-memory state only** — no persistence; restart loses the chain. *Next:*
  back the account/chain state with LevelDB/SQLite.
- **Nonce is tracked at mempool-admission, not block-application** — so the
  full-chain *replay* path (`replace_chain`) doesn't reconstruct nonces. A known
  inconsistency I'd unify next by moving nonce accounting entirely into `_apply_tx`.
- **Account key vs. address** — the chain keys accounts by raw public key, while
  `wallet.py` computes a Bitcoin-style `RIPEMD160(SHA256(pubkey))` address that
  isn't yet wired into the ledger.
- **Minimal P2P** — broadcast + longest-chain sync only; no real fork-choice,
  gossip, or peer discovery. It's a demo, not production networking.
- **No mempool economics** — no fee-based ordering or block size limit.
- **PoS seed is `sha256(prev_hash)`** — deterministic but theoretically grindable;
  real chains mix in randomness (RANDAO/VRF).

Framing: *"These are deliberate scope cuts for a learning project — I kept the
focus on consensus and cryptographic mechanics rather than persistence and
networking infrastructure."*

---

## 10. Anticipated interview Q&A

**Q: Account-based vs. UTXO — why?**
Account model: simpler mental model (balances in a dict), natural fit for
stake/escrow state, and what Ethereum uses. UTXO (Bitcoin) parallelizes better and
has nicer privacy properties but is more complex to implement. I chose accounts to
keep the focus on consensus.

**Q: What stops me from spending someone else's coins?**
The signature. `verify()` reconstructs the public key from the `sender` field and
checks the ECDSA signature over the canonical tx body. No private key, no valid
signature, no spend.

**Q: What stops a replay attack?**
Per-account nonces. A tx is only valid if its nonce is exactly one more than the
account's current nonce, and the nonce advances on admission, so the same signed tx
can't be applied twice.

**Q: How does the Merkle root help?**
It's a single hash committing to all transactions. The block hash includes the root,
so changing any transaction changes the root → changes the block hash → breaks the
link to every subsequent block. It also enables succinct membership proofs (didn't
implement proofs here, but the structure supports them).

**Q: Walk me through PoS validator selection.**
Deterministic stake-weighted lottery: hash the previous block to get a seed, take it
modulo total stake, then walk staked accounts accumulating stake until you cross the
seed point. Higher stake = proportionally higher chance. The chosen validator must
be the one who actually produced the block.

**Q: What is slashing and why does PoS need it?**
PoS replaces energy cost with capital cost — but capital only deters cheating if it
can be *destroyed*. Slashing burns half a validator's stake when they double-sign
(produce two blocks at one height). I detect it both in-protocol and via a `SLASH`
transaction that carries verifiable evidence.

**Q: How do you know an incoming chain is valid?**
Replay it from genesis on fresh state through `_validate_chain`, which checks each
block header (`_check_block`) and re-applies every transaction with full validation
(`_apply_tx(validate=True)`). I adopt it only if it's strictly longer and fully valid.

**Q: Tell me about a bug you fixed.**
The escrow-claim check was inverted in one of three duplicated validation copies — it
rejected the correct secret. The root cause was *duplication*: the same logic existed
three times and had drifted. I unified it into one `_apply_tx`, which fixed the bug
and made that class of bug impossible going forward.

---

## 11. Live demo cheat-sheet

```bash
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -e ".[dev]"
python -m pytest -q                                  # 9 passed

python -m uvicorn pychain.api:app --reload --port 5000
# → open http://127.0.0.1:5000/docs  (interactive Swagger UI)
```

Golden path in Swagger:
1. `POST /faucet` — fund an address.
2. `GET /balance/{addr}` — see the balance/nonce/stake.
3. `POST /mine?miner=<addr>` — mine a block.

(Signed `POST /tx` is best demonstrated via `scripts/` rather than hand-typed, since
it needs a real ECDSA signature.)

---

### One-line takeaways to memorize
- *"Account-based ledger, ECDSA-signed txs, Merkle-committed blocks."*
- *"Two consensus algorithms behind one flag, with slashing for PoS."*
- *"One parameterized state transition powers apply, validate-block, and validate-chain."*
- *"I found the duplication, proved it had caused bugs, unified it, and added tests."*
