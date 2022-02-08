import select
import time
from socket import socket, AF_INET, SOCK_STREAM
from utils import send_msg, take_msg, load_config, load_args
from logs.server_log_config import logger


def read_requests(r_clients, all_clients):
   responses = []
   for sock in r_clients:
       try:
           data = take_msg(sock)
           print(data)
           responses.append(data)
       except:
           print('Клиент {} {} отключился'.format(sock.fileno(), sock.getpeername()))
           all_clients.remove(sock)

   return responses


def write_responses(requests, w_clients, all_clients, users):
   for msg in range(len(requests)):
       sock = users[requests[msg]['DESTINATION']]
       print('msg='+msg)
       print('requests='+requests)
       try:
           print(sock)
           send_msg(requests[msg], sock)
       except:
           print('Клиент {} {} отключился'.format(sock.fileno(), sock.getpeername()))
           sock.close()
           all_clients.remove(sock)


def gen_answer(client_msg):
    answer = {
        "RESPONSE": 200,
        "TIME": time.time(),
        "ALERT": f'{client_msg["USER"]["ACCOUNT_NAME"]} knocked!'
    }
    if client_msg['ACTION'] == 'presence' and client_msg['TIME'] and client_msg['USER']['ACCOUNT_NAME']:
        return answer
    else:
        answer['RESPONSE'] = 400
        answer['ALERT'] = 'bad request'
        logger.error('Данные от клиента не пришли или пришли некорректно')
        return answer


def main():
    configs = load_config()
    args = load_args(configs)
    s = socket(AF_INET, SOCK_STREAM)
    s.bind((args.a, args.p))
    s.listen(configs['MAX_CONNECTIONS'])

    clients = []
    users = {}

    while True:
        try:
            client, addr = s.accept()
            client_message = take_msg(client)
        except OSError:
            logger.error('OS error')
        else:
            logger.info(f'{client_message["USER"]["ACCOUNT_NAME"]} send {client_message["ACTION"]} message')
            send_msg(gen_answer(client_message), client)
            clients.append(client)
            users[client_message["USER"]["ACCOUNT_NAME"]] = client
            print(f'{client_message["USER"]["ACCOUNT_NAME"]} подключен')

        readable = []
        writeble = []
        try:
            if clients:
                readable, writeble, e = select.select(clients, clients, [])

        except:
            print('Сбой при подключении')
        requests = read_requests(readable, clients)
        if requests:
            write_responses(requests, writeble, clients, users)


if __name__ == '__main__':
    main()
