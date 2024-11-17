import bcrypt


def hash_mnemonic(mnemonic: str) -> str:
    salt = bcrypt.gensalt()
    mnemonic_hash = bcrypt.hashpw(mnemonic.encode(), salt)
    return mnemonic_hash.decode()


def verify_mnemonic(mnemonic: str, hashed: str) -> bool:
    return bcrypt.checkpw(mnemonic.encode(), hashed.encode())
