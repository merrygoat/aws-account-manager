class Config:
    DEBUG = True
    FLASK_APP = "aam"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///../aam/data.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "abc123"
    TEMPLATES_AUTO_RELOAD = False


class Production(Config):
    DEBUG = False
    TEMPLATES_AUTO_RELOAD = False
