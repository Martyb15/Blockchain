import hashlib
from ecdsa import SigningKey, VerifyingKey, SECP256k1

def gen_keypair():
    """Return (priv_pem, pub_pem) as bytes."""
    sk = SigningKey.generate(curve=SECP256k1)
    vk = sk.verifying_key
    return sk.to_pem(), vk.to_pem()

def address_from_pub_pem(pub_pem: bytes) -> str:
    """addr = RIPEMD160(SHA256(compressed_pubkey)) in hex."""
    vk = VerifyingKey.from_pem(pub_pem)
    pub_bytes = vk.to_string("compressed")  # 33 bytes
    h = hashlib.sha256(pub_bytes).digest()
    ripemd = hashlib.new("ripemd160", h).hexdigest()
    return "0x" + ripemd