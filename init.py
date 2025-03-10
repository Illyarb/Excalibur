from db_operations import create_db
from config import db_path
import os
from pathlib import Path



if not os.path.exists(Path(db_path).expanduser()):
    os.makedirs(Path(db_path).expanduser())
if not os.path.exists(Path(db_path + "/scripts").expanduser()):
    os.makedirs(Path(db_path + "/scripts").expanduser())
if not os.path.exists(Path(db_path + "/cards").expanduser()):
    os.makedirs(Path(db_path + "/cards").expanduser())
create_db()
