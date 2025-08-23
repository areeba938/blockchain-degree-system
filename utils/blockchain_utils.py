from .crypto import calculate_hash
from datetime import datetime
import json
import os

def utcnow_iso():
    """Return UTC timestamp without microseconds"""
    return datetime.utcnow().replace(microsecond=0).isoformat()
def format_timestamp(ts):
    """Return ISO string (no microseconds). Accepts datetime or str."""
    if isinstance(ts, datetime):
        return ts.replace(microsecond=0).isoformat()
    if isinstance(ts, str):
        # If contains '.', cut microseconds: "2025-08-22T19:14:15.291723" -> "2025-08-22T19:14:15"
        return ts.split('.')[0] if '.' in ts else ts
    return str(ts)


class Block:
    def __init__(self, index, previous_hash, timestamp, data, nonce):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data
        self.nonce = nonce
        self.hash = calculate_hash(index, previous_hash, timestamp, data, nonce)

    def to_dict(self):
        # Ensure datetime is in ISO format string
        timestamp_str = format_timestamp(self.timestamp)



        # Ensure data is sorted before saving
        sorted_data = json.loads(json.dumps(self.data, sort_keys=True))

        return {
             "index": self.index,
             "previous_hash": self.previous_hash,
             "timestamp": timestamp_str,
             "data": sorted_data,
             "nonce": self.nonce,
             "hash": self.hash
        }



    def recalculate_hash(self):
        return calculate_hash(
            self.index,
            self.previous_hash,
            self.timestamp,
            self.data,
            self.nonce
        )

    def is_valid(self):
        return self.hash == self.recalculate_hash()


class BlockchainUtils:
    @staticmethod
    def build_block(index, previous_hash, timestamp, data, nonce):
        """
        Create a block dict with consistent structure for both DB and JSON
        """
        ts = format_timestamp(timestamp)  # ✅ normalize timestamp
        sorted_data = json.loads(json.dumps(data, sort_keys=True))  # ✅ sort keys

        block_hash = calculate_hash(
            int(index),
            str(previous_hash),
            ts,
            sorted_data,
            int(nonce)
        )
        return {
        "index": int(index),
        "previous_hash": str(previous_hash),
        "timestamp": ts,
        "data": sorted_data,
        "nonce": int(nonce),
        "hash": block_hash
    }

    @staticmethod
    def create_genesis_block():
        static_timestamp = "2025-01-01T00:00:00"  # FIXED timestamp for determinism

        genesis_data = {
             "id": 0,
             "student_id": "0000",
             "degree_name": "Genesis Degree",
             "institution": "Blockchain Authority",
             "year_awarded": 2024,
             "field_of_study": "Genesis Block",
             "created_at": static_timestamp,
              "message": "This is the Genesis Block"
       }
        block = Block(0, "0", static_timestamp, genesis_data, 0)
        return block.to_dict()

    @staticmethod
    def generate_block(last_block, data):
        index = last_block.id + 1
        previous_hash = last_block.current_hash
        timestamp = utcnow_iso()
        timestamp = format_timestamp(timestamp)

        nonce = 0
        sorted_data = json.loads(json.dumps(data, sort_keys=True))
        block = Block(index, previous_hash, timestamp, sorted_data, nonce)
        return block.to_dict()
        

    @staticmethod
    def validate_block(block, previous_block):
        sorted_data = json.loads(json.dumps(block['data'], sort_keys=True))
        expected_hash = calculate_hash(
            block['index'],
            block['previous_hash'],
            block['timestamp'],
            sorted_data,
            block['nonce']
        )
        return (
            block['previous_hash'] == previous_block['hash']
            and block['hash'] == expected_hash
        )


    @staticmethod
    def validate_chain(chain):
        if len(chain) == 0:
            return False

        expected = BlockchainUtils.create_genesis_block()
        if json.dumps(chain[0], sort_keys=True) != json.dumps(expected, sort_keys=True):
            return False

        for i in range(1, len(chain)):
            if not BlockchainUtils.validate_block(chain[i], chain[i - 1]):
                return False

        return True


def is_certificate_on_blockchain(degree_id):
    try:
        path = os.path.join(os.path.dirname(__file__), '..', 'data', 'blockchain.json')
        path = os.path.abspath(path)

        with open(path, 'r') as f:
            blockchain_data = json.load(f)

        for block in blockchain_data:
            if isinstance(block, dict) and block.get("data", {}).get("degree_id") == degree_id:
                return True

        return False

    except Exception as e:
        print("Blockchain check error:", str(e))
        return False