import hashlib
import json
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from datetime import datetime


def calculate_hash(index, previous_hash, timestamp, data, nonce):
    """
    Canonical SHA256 hash for a block.
    - `timestamp` must be a string (ISO, no microseconds).
    - `data` must be a plain dict with keys sorted.
    """
    # Ensure data is JSON-serializable with sorted keys
    normalized_data = json.loads(json.dumps(data, sort_keys=True))

    payload = {
        "index": int(index),
        "previous_hash": str(previous_hash),
        "timestamp": str(timestamp),
        "data": normalized_data,
        "nonce": int(nonce)
    }

    # Deterministic JSON: sort keys and remove unnecessary spaces
    block_string = json.dumps(payload, sort_keys=True, separators=(',', ':'))

    return hashlib.sha256(block_string.encode('utf-8')).hexdigest()


def generate_key_pair():
    key = RSA.generate(2048)
    private_key = key.export_key()
    public_key = key.publickey().export_key()
    return private_key, public_key

def sign_data(private_key, data):
    key = RSA.import_key(private_key)
    h = SHA256.new(json.dumps(data,sort_keys=True).encode())
    signature = pkcs1_15.new(key).sign(h)
    return signature.hex()

def verify_signature(public_key, data, signature):
    key = RSA.import_key(public_key)
    h = SHA256.new(json.dumps(data,sort_keys=True).encode())
    try:
        pkcs1_15.new(key).verify(h, bytes.fromhex(signature))
        return True
    except (ValueError, TypeError):
        return False