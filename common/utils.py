import argparse
from common.variables import *
from errors import IncorrectDataRecivedError, NonDictInputError
import json
import sys
sys.path.append('../')
from decos import *


# Утилита приёма и декодирования сообщения
# принимает байты выдаёт словарь, если приняточто-то другое отдаёт ошибку значения
@log
def get_message(client):
    encoded_response = client.recv(MAX_PACKAGE_LENGTH)
    if isinstance(encoded_response, bytes):
        json_response = encoded_response.decode(ENCODING)
        response = json.loads(json_response)
        if isinstance(response, dict):
            return response
        else:
            raise IncorrectDataRecivedError
    else:
        raise IncorrectDataRecivedError


# Утилита кодирования и отправки сообщения
# принимает словарь и отправляет его
@log
def send_message(sock, message):
    if not isinstance(message, dict):
        raise NonDictInputError
    js_message = json.dumps(message)
    encoded_message = js_message.encode(ENCODING)
    sock.send(encoded_message)


# Парсер аргументов коммандной строки
@log
def arg_parser(server=True):
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', default=DEFAULT_IP_ADDRESS if server == False else '', nargs='?')
    parser.add_argument('-p', default=None, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.a
    server_port = namespace.p
    client_name = namespace.name
    return server_address, server_port, client_name

