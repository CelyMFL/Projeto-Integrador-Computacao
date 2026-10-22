from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_USERNAME = os.getenv("DATABASE_USERNAME")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_PORT = os.getenv("DATABASE_PORT", "3306")
DATABASE_NAME = os.getenv("DATABASE_NAME")
DATABASE_SSL_VERIFY_CERT = os.getenv("DATABASE_SSL_VERIFY_CERT", "true").lower() == "true"

SQLALCHEMY_DATABASE_URI = (
    f"mysql+pymysql://{DATABASE_USERNAME}:{DATABASE_PASSWORD}"
    f"@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
    + ("?ssl_verify_cert=true" if DATABASE_SSL_VERIFY_CERT else "")
)

SQLALCHEMY_TRACK_MODIFICATIONS = False

SECRET_KEY = os.getenv("SECRET_KEY")