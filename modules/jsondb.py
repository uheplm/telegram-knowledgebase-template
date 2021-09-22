import json
from os import path
from functools import reduce  # forward compatibility for Python 3
import operator
import yaml
class JSONDB(object):
    def __init__(self, filename):
        self._filename = filename
        if path.exists(filename):
            file = open(filename, 'r', encoding='utf8')
            if file.read() == "":
                file = open(filename, 'w', encoding='utf8')
                file.write('')
            file.close()
        else:
            file = open(filename, 'w', encoding='utf8')
            file.write('')
            file.close()
        with open(filename, encoding='utf8') as data:
            self._data = yaml.load(data)

    def get(self, string = ''):
        query = string if type(string) is list else string.split('.')
        if string == '':
            return self._data
        else:
            try:
                return reduce(operator.getitem, query, self._data)
            except Exception as E:
                return None

