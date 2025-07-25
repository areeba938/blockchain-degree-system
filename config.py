import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-very-secret-key-123')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://postgres:1234@localhost/degree_verification')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMIN_USERNAMES = ['admin1', 'admin2', 'admin3']
    BLOCKCHAIN_DIFFICULTY = 0
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ''))
    JSON_STORAGE_PATH = os.path.join(BASE_DIR, 'data', 'blockchain.json')
