from flask import Flask
from enum import IntEnum, auto

class Stats(IntEnum):
    GOAL = 0
    ASSIST = auto()
    CALLAHAN = auto()
    POSSESSION = auto()
    BLOCK = auto()
    CATCH_BLOCK = auto()
    DROP = auto()
    THROW_AWAY = auto()
    COUNT = auto()

class Actions(IntEnum):
    GOAL = 0
    DEFENSE = auto()
    DROP = auto()
    THROW_AWAY = auto()
    COUNT = auto()

global db_connector
APP = Flask(__name__)
logger = APP.logger

from ultimate_stats_tracker import mysql_connector
db_connector = mysql_connector.MySQLConnector(list(Stats.__members__.keys())[:-1]);

from ultimate_stats_tracker import api
from ultimate_stats_tracker import frontend