import hashlib
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import ec

def gen_keypair() -> tuple[str, str]:
    """Return (priv_pem, pub_pem) - same format as transaction.py"""
    priv     = ec.generate_private_key(ec.SECP256K1())
    priv_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.NoEncryption(),
    ).decode()
    pub_hex = priv.public_key().public_bytes(
        serialization.Encoding.X962, 
        serialization.PublicFormat.UncompressedPoint,
    ).hex()
    return priv_pem, pub_hex

def address_from_pub_pem(pub_hex: str) -> str:
    """addr = RIPEMD160(SHA256(pubkey)) in hex."""
    pub_bytes = bytes.fromhex(pub_hex)
    h = hashlib.sha256(pub_bytes).digest()
    ripemd = hashlib.new("ripemd160", h).hexdigest()
    return "0x" + ripemd
