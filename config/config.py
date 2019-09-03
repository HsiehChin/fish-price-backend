import os
import yaml
from pymongo import MongoClient


class Config(object):
    def __init__(self):
        self.__path = os.path.dirname(__file__)
        self.__db = self.__set_db()

    def __set_db(self):
        path = os.path.join(self.__path, "db.yaml")
        with open(path, "r") as file:
            config = yaml.full_load(file)
            uri = "mongodb://{user}:{password}@{host}:{port}".format(
                user=config["user"],
                password=config["password"],
                host=config["host"],
                port=config["port"],
            )
            return MongoClient(uri)
        return None

    @property
    def db(self):
        return self.__db
