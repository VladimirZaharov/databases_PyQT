import logging
from logging.handlers import TimedRotatingFileHandler
import os


logger = logging.getLogger('messenger.server')
formatter = logging.Formatter("%(asctime)s   %(levelname)-10s %(module)-10s %(message)s ")

PATH = os.path.dirname(__file__)
PATH = os.path.join(PATH, 'server.log')

server_file_handler = TimedRotatingFileHandler(PATH, when='midnight', interval=1,
                                               backupCount=10, encoding='utf-8')
server_file_handler.setLevel(logging.INFO)
server_file_handler.setFormatter(formatter)
logger.addHandler(server_file_handler)
logger.setLevel(logging.INFO)
