import secrets
import hashlib
from mnemonic import Mnemonic


class Hash:
    @staticmethod
    def generate_password() -> str:
        return secrets.token_hex(8)

    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return Hash.hash_password(plain_password) == hashed_password

    @staticmethod
    def generate_mnemonic_phrase() -> str:
        mnemo = Mnemonic("english")
        entropy = secrets.randbits(128)
        words = mnemo.to_mnemonic(entropy.to_bytes(16, 'big'))
        return words
