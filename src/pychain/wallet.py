import hashlib
from dataclasses import dataclass
from src.pychain.transaction import gen_keypair

def address_from_pub_hex(pub_hex: str) -> str:
    """addr = RIPEMD160(SHA256(pubkey)) in hex."""
    pub_bytes = bytes.fromhex(pub_hex)
    h = hashlib.sha256(pub_bytes).digest()
    ripemd = hashlib.new("ripemd160", h).hexdigest()
    return "0x" + ripemd

@dataclass
class Wallet: 
    priv_pem: str
    pub_hex:  str
    address:  str

    @classmethod
    def generate(cls) -> "Wallet": 
        prive_pem, pub_hex = gen_keypari()
        return cls(
            prive_pem=priv_pem, 
            pub_hex=pub_hex, 
            address=address_from_pub_hex(pub_hex),
        )
