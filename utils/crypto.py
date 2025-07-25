import hashlib
import json
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from datetime import datetime

def calculate_hash(index, previous_hash, timestamp, data, nonce):
    block_string = f"{index}{previous_hash}{timestamp}{json.dumps(data, sort_keys=True, separators=(',', ':'))}{nonce}"
    return hashlib.sha256(block_string.encode()).hexdigest()


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