import hashlib

def sha256_hash(input_string: str) -> str:
    """Generates a SHA-256 hash for the given input string."""
    sha256 = hashlib.sha256()
    sha256.update(input_string.encode('utf-8'))
    return sha256.hexdigest()