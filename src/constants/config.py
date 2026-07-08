import os, shutil
from sqlalchemy import create_engine
import datetime
import time
import environment

# App config


class APP_CONFIG:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    HOST = environment.HOST
    PORT = int(environment.PORT)

    # Mode config
    MODE = environment.MODE.lower()
    DEBUG = True

    # Database config
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{environment.DB_USER}:{environment.DB_PASSWORD}"
        f"@{environment.DB_HOST}:{environment.DB_PORT}/{environment.DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False


# Token config
if environment.MODE == "dev":
    EXPIRES_DELTA_TOKEN = datetime.timedelta(days=1000)
else:
    EXPIRES_DELTA_TOKEN = datetime.timedelta(days=1)
