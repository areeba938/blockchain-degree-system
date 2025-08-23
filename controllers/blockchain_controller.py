from my_models import db, Block, Degree, Approval, Admin, Student
from utils.blockchain_utils import BlockchainUtils
from utils.crypto import calculate_hash
from datetime import datetime
from werkzeug.security import generate_password_hash
import json
from my_models import Student
from flask import current_app
import os
from utils.blockchain_utils import utcnow_iso, format_timestamp

def utcnow_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat()

class BlockchainController:
    VALID_ADMIN_USERNAMES = ['admin1', 'admin2', 'admin3']
    @staticmethod
    def initialize_blockchain():
    # 🔧 Set up file path
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        json_path = current_app.config.get('JSON_STORAGE_PATH') if hasattr(current_app, 'config') else None
        if not json_path:
            json_path = os.path.join(base_dir, 'data', 'blockchain.json')
        os.makedirs(os.path.dirname(json_path), exist_ok=True)

    # ✅ First, check DB: if already initialized, skip
        if Block.query.count() > 0:
            print("🔁 Blockchain already initialized in database.")
            return

        print("🧱 Creating genesis block in DB + JSON...")

    # Genesis student
        genesis_student = Student(
            student_id='GENESIS_STUDENT',
            full_name='Genesis Student',
            email='genesis@example.com',
            password_hash=generate_password_hash('secure_password')
       )
        db.session.add(genesis_student)
        db.session.commit()

    # Genesis degree
        genesis_degree = Degree(
            degree_name='Genesis Degree',
            student_id='GENESIS_STUDENT',
            institution='Blockchain Authority',
            field_of_study='Genesis Block',
            year_awarded=2025,
            created_at=utcnow_iso()
        )
        db.session.add(genesis_degree)
        db.session.flush()  # just get id

    # ✅ Build genesis block with BlockchainUtils
        block_obj = BlockchainUtils.create_genesis_block()
         # Save to DB — convert timestamp string -> datetime
        try:
            ts_dt = datetime.fromisoformat(block_obj["timestamp"])
        except Exception:
            # fallback: parse without 'T' -> attempt replace
            try:
                ts_dt = datetime.fromisoformat(block_obj["timestamp"].replace(' ', 'T'))
            except Exception:
                # last resort: use current UTC truncated
                ts_dt = datetime.utcnow().replace(microsecond=0)

    # Save in DB
        genesis_block = Block(
            previous_hash=block_obj.get("previous_hash"),
            current_hash=block_obj.get("hash"),
            degree_id=genesis_degree.id,
            timestamp=ts_dt,
            nonce=block_obj.get("nonce", 0),
            approved=True
        )
        db.session.add(genesis_block)
        db.session.commit()

    # Save same block to JSON file
        with open(json_path, 'w') as f:
            json.dump([block_obj], f, indent=4)

        print("✅ Genesis block added to DB + JSON (consistent).")

    @staticmethod
    def add_degree_to_blockchain(degree_id):
        """Add a degree to blockchain (pending approval)"""
        degree = Degree.query.get(degree_id)
        if not degree:
            return False, "Degree not found"
        degree_count = Degree.query.filter_by(student_id=degree.student_id).filter(Degree.status != 'Rejected').count()

        if degree_count >= 3:
            return False, "You have already submitted 2 degrees. Further submissions are not allowed."
        last_block = Block.query.order_by(Block.id.desc()).first()
        if not last_block:
            return False, "Blockchain not initialized"

        # Prepare degree data
        degree_data = {
            'id': int(degree.id),
            'student_id': str(degree.student_id),
            'degree_name': degree.degree_name,
            'institution': degree.institution,
            'year_awarded': int(degree.year_awarded),
            'field_of_study': degree.field_of_study,
            'created_at': format_timestamp(degree.created_at)
        }
        ts = utcnow_iso()

        index = int(last_block.id) + 1
        previous_hash = last_block.current_hash
        new_block_data = BlockchainUtils.generate_block(last_block, degree_data)

        # Prevent tampering by checking hash linkage
        if new_block_data['previous_hash'] != last_block.current_hash:
            return False, "Hash mismatch: rejecting block"

        # Create and store new block
        db_ts = datetime.fromisoformat(new_block_data['timestamp'])

        new_block = Block(
            previous_hash=new_block_data['previous_hash'],
            current_hash=new_block_data['hash'],
            degree_id=degree.id,
            timestamp=db_ts,
            nonce=new_block_data['nonce'],
            approved=False
        )

        db.session.add(new_block)
        db.session.commit()

        return True, "Degree added to blockchain pending approval"

    @staticmethod
    def approve_block(block_id, admin_id):
        """Process block approval by admin"""
        block = Block.query.get(block_id)
        if not block:
            return False, "Block not found"

        admin = Admin.query.get(admin_id)
        if not admin:
            return False, "Admin not found"

        # Prevent duplicate approvals
        if Approval.query.filter_by(block_id=block_id, admin_id=admin_id).first():
            return False, "Admin already approved this block"

        # Record approval
        new_approval = Approval(
            block_id=block_id,
            admin_id=admin_id,
            approval_status=True
        )
        db.session.add(new_approval)

        # Check for 3 approvals
        approval_count = Approval.query.filter_by(
            block_id=block_id,
            approval_status=True
        ).count()

        if approval_count >= 3:
            # ✅ Validate that all approvals are from valid admins
            all_approvals = Approval.query.filter_by(block_id=block_id, approval_status=True).all()
            for approval in all_approvals:
                approving_admin = Admin.query.get(approval.admin_id)
                if approving_admin.username not in BlockchainController.VALID_ADMIN_USERNAMES:
                    return False, f"Unauthorized admin '{approving_admin.username}' detected. Rejecting block."

            block.approved = True

            # Ensure blockchain integrity before adding
            if not BlockchainController._is_valid_chain_addition(block):
                return False, "Chain integrity invalid. Block not added."

            BlockchainController._add_to_json_blockchain(block)
            db.session.commit()
            return True, "Degree fully approved and added to blockchain"

        db.session.commit()
        return True, "Approval recorded (awaiting more approvals)"

    @staticmethod
    def _is_valid_chain_addition(block):
        """Check if new block correctly extends the chain"""
        try:
            with open(current_app.config['JSON_STORAGE_PATH'], 'r') as f:
                chain = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return False

        if not chain:
            return False

        last_block = chain[-1]
        return block.previous_hash == last_block['hash']
    @staticmethod
    def _add_to_json_blockchain(block):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        blockchain_file = os.path.join(base_dir, 'data', 'blockchain.json')

        degree = Degree.query.get(block.degree_id)
        if not degree:
            print(f"❌ Degree not found for ID: {block.degree_id}")
            return

        # Load existing chain
        if os.path.exists(blockchain_file):
            with open(blockchain_file, 'r') as f:
                blockchain = json.load(f)
        else:
            blockchain = []

        index = int(block.id)                       # 🔑 use DB id (same as in calculate_hash)
        previous_hash = str(block.previous_hash)    # 🔑 take from DB, not len(chain)
        ts = format_timestamp(block.timestamp)

        degree_data = {
            'id': int(degree.id),
            'student_id': str(degree.student_id),
            'degree_name': degree.degree_name,
            'institution': degree.institution,
            'year_awarded': int(degree.year_awarded),
            'field_of_study': degree.field_of_study,
            'created_at': format_timestamp(degree.created_at)
       }

        new_block = BlockchainUtils.build_block(
            index=index,
            previous_hash=previous_hash,
            timestamp=ts,
            data=degree_data,
            nonce=int(block.nonce)
        )


        blockchain.append(new_block)

        with open(blockchain_file, 'w') as f:
            json.dump(blockchain, f, indent=4)

        print("✅ Block successfully written to blockchain.json")


    @staticmethod
    def verify_degree(identifier):
        blockchain_file = current_app.config['JSON_STORAGE_PATH']

        if not os.path.exists(blockchain_file):
            return False, "Blockchain not initialized or missing."

        with open(blockchain_file, 'r') as f:
            try:
                blockchain = json.load(f)
            except json.JSONDecodeError:
                return False, "Blockchain file corrupted."
   
        for block in blockchain:
        # Either search by hash or by degree id (convert string to int if needed)
            if block['hash'] == identifier or str(block['data'].get('id')) == identifier:
            # ✅ Recalculate the hash to check tampering
                sorted_data = json.loads(json.dumps(block['data'], sort_keys=True))

                recalculated_hash = calculate_hash(
                    block['index'],
                    block['previous_hash'],
                    block['timestamp'],
                    sorted_data,
                    block['nonce']
                )

                if recalculated_hash != block['hash']:
                     return False, "Block has been tampered with and is invalid"

            # ✅ Pull the correct values to display
                return True, {
                    'degree_id': block['data'].get('id'),
                    'student_id': block['data'].get('student_id'),
                    'degree_name': block['data'].get('degree_name'),
                    'institution': block['data'].get('institution'),
                    'year_awarded': block['data'].get('year_awarded'),
                    'verification_hash': block['hash'],
                    'timestamp': block['timestamp'],
                    'block_index': block['index']
                }

        return False, "Hash or Degree ID not found in blockchain."
   


    @staticmethod
    def _verify_by_degree_id(degree_id):
        block = Block.query.filter_by(degree_id=degree_id, approved=True).first()
        if not block:
            return False, f"Degree ID {degree_id} not found or not approved"
        return BlockchainController._get_verification_result(block)

    @staticmethod
    def _verify_by_hash(degree_hash):
        block = Block.query.filter_by(current_hash=degree_hash, approved=True).first()
        if not block:
            return False, f"Hash {degree_hash[:8]}... not found or not approved"
        return BlockchainController._get_verification_result(block)

    @staticmethod
    def _get_verification_result(block):
        try:
            with open(current_app.config['JSON_STORAGE_PATH'], 'r') as f:
                blockchain = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return False, "Blockchain data file corrupted"

        block_data = next((b for b in blockchain if isinstance(b, dict) and b.get('hash') == block.current_hash), None)
        if not block_data:
            return False, "Degree not found in blockchain records"

        degree = block.degree
        if not degree:
            return False, "Degree details not found"
       # 🔄 Ensure consistent ordering for hashing
        sorted_data = json.loads(json.dumps(block_data['data'], sort_keys=True))

        recalculated_hash = calculate_hash(
            block_data['index'],
            block_data['previous_hash'],
            block_data['timestamp'],
            sorted_data,
            block_data['nonce']
        )

        print("🔎 VERIFICATION DEBUG")
        print("🧩 Sorted data used for hash:", sorted_data)
        print("Recalculated Hash:", recalculated_hash)
        print("Index:           ", block_data['index'])
        print("Previous Hash:   ", block_data['previous_hash'])
        print("Data:            ", block_data['data'])
        print("Timestamp:       ", block_data['timestamp'])
        print("Nonce:           ", block_data['nonce'])
        print("📦 BLOCK FROM JSON")
        print(json.dumps(block_data, indent=2))

 
        if recalculated_hash != block_data['hash']:
            return False, "Block has been tampered with and is invalid"

        # ✅ Only use data from block_data['data'] (not from DB)
        block_data['data']

        return True, {
            'degree_id': degree.id,
            'student_id': degree.student_id,
            'degree_name': degree.degree_name,
            'institution': degree.institution,
            'year_awarded': degree.year_awarded,
            'verification_hash': block.current_hash,
            'timestamp': block.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'block_index': block_data.get('index', 'unknown')
        }

    @staticmethod
    def _validate_blockchain(block_data, blockchain):
        try:
            index = block_data['index']
            if index == 0:
                return block_data == BlockchainUtils.create_genesis_block()
            if index >= len(blockchain):
                return False
            return BlockchainUtils.validate_block(block_data, blockchain[index - 1])
        except (KeyError, IndexError):
            return False

    @staticmethod
    def get_blockchain():
        try:
            with open(current_app.config['JSON_STORAGE_PATH'], 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return [BlockchainUtils.create_genesis_block()]

    @staticmethod
    def get_blockchain_blocks():
        return Block.query.order_by(Block.id).all()