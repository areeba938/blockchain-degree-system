from .crypto import calculate_hash
from datetime import datetime
import json
import os


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
        timestamp_str = self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp)

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
    def create_genesis_block():
        static_timestamp = datetime.utcnow().isoformat()

        genesis_data = {
            "message": "Genesis Block",
            "timestamp": static_timestamp
        }
        block = Block(0, "0", static_timestamp, genesis_data, 0)
        return block.to_dict()

    @staticmethod
    def generate_block(last_block, data):
        index = last_block.id + 1
        previous_hash = last_block.current_hash
        timestamp = datetime.utcnow().isoformat()
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