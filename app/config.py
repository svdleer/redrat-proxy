import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
    MYSQL_DB = os.getenv('MYSQL_DB', 'redrat_proxy')
    MYSQL_USER = os.getenv('MYSQL_USER', 'redrat')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'password')
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'app/static/uploads')
    REDRAT_XMLRPC_URL = os.getenv('REDRAT_XMLRPC_URL', 'http://localhost:40000/RPC2')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')