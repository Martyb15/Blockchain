from dataclasses import dataclass, asdict
from typing import Optional
import json, hashlib, secrets
from config import JSON_SEP
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature


def gen_keypair() -> tuple[str, str]:
    """
    Returns (private_pem, public_hex)
    """
    priv = ec.generate_private_key(ec.SECP256K1())
    priv_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    pub_hex = priv.public_key().public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    ).hex()
    return priv_pem, pub_hex


@dataclass(frozen=True)
class Transaction:
    """
    Three kinds:
      PAY          sender → recipient
      OPEN_REMIT   escrow contract
      CLAIM_REMIT  claim funds
    """
    tx_type: str          # "PAY"|"OPEN_REMIT"|"CLAIM_REMIT"|"STAKE"|"UNSTAKE"
    sender: str
    recipient: str | None
    amount: int
    fee: int
    nonce: int
    payload: Optional[dict] = None  # e.g. {"release_hash": "..."}
    signature: Optional[str] = None

    # ---------- helpers ----------
    def _body(self) -> bytes:
        d = asdict(self)
        d.pop("signature")
        return json.dumps(d, sort_keys=True, separators=JSON_SEP).encode()

    def hash(self) -> str:
        return hashlib.sha256(self._body()).hexdigest()

    # ---------- signing ----------
    def sign(self, private_pem: str) -> None:
        priv = serialization.load_pem_private_key(private_pem.encode(), None)
        sig = priv.sign(self._body(), ec.ECDSA(hashes.SHA256()))
        object.__setattr__(self, "signature", sig.hex())

    def verify(self) -> bool:
        from cryptography.hazmat.primitives.asymmetric import ec
        if self.signature is None:
            return False
        try:
            pub_bytes = bytes.fromhex(self.sender)
            pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256K1(), pub_bytes)
            pub.verify(bytes.fromhex(self.signature), self._body(), ec.ECDSA(hashes.SHA256()))
            return True
        except (ValueError, InvalidSignature):
            return False
        
    def to_dict(self) -> dict:
        return {
            "tx_type": self.tx_type,
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "fee": self.fee,
            "nonce": self.nonce,
            "payload": self.payload,
            "signature": self.signature,
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        tx = cls(
            tx_type=data["tx_type"],
            sender=data["sender"],
            recipient=data["recipient"],
            amount=data["amount"],
            fee=data["fee"],
            nonce=data["nonce"],
            payload=data.get("payload"),
            signature=data.get("signature"),
        )
        return tx