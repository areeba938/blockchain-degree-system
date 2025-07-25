from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()  # Initialize db here

# Import all models after db is created
from .admin import Admin
from .student import Student
from .degree import Degree
from .blockchain import Block
from .approval import Approval

__all__ = ['db', 'Admin', 'Student', 'Degree', 'Block', 'Approval']