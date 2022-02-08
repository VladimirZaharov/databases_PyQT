import sys
import threading
from socket import socket, AF_INET, SOCK_STREAM
from utils import send_msg, take_msg, load_config, load_args
import time
from logs.client_log_config import logger


def gen_msg(user_name, action, destination='server', message=''):
    msg = {
        "ACTION": action,
        "TIME": time.time(),
        "USER": {
            "ACCOUNT_NAME": user_name,
            "STATUS": "Yep, I am here!"
        },
        "DESTINATION": destination,
        "MESSAGE": message
    }
    return msg


def user_interactive(sock, username, thread_lock):
    while True:
        to_user = input('Введите получателя сообщения (exit - для выхода):')
        message = input('Введите сообщение для отправки: ')
        if to_user == 'exit':
            break
        else:
            try:
                msg = gen_msg(username, 'message', to_user, message)
                send_msg(sock, msg)
            except:
                print(f'Ошибка отправки сообщения для {to_user}')
                sys.exit(1)


def message_from_server(sock):
    while True:
        try:
            message = take_msg(sock)
            print(f'{message["USER"]["ACCOUNT_NAME"]}: {message["MESSAGE"]}')
        except:
            print(f'Ошибка принятия сообщения от сервера')
            sys.exit(1)


def main():
    resource_lock = threading.Lock()
    configs = load_config()
    args = load_args(configs)
    s = socket(AF_INET, SOCK_STREAM)
    s.connect((args.a, args.p))
    username = input('Введите ваше имя: ')
    send_msg(gen_msg(username, 'presence'), s)
    msg_from_server = take_msg(s)
    logger.info(f'server answered: {msg_from_server["ALERT"]}')
    if msg_from_server['RESPONSE'] == 200:
        print(f'Вы удачно подключены к серверу')
    else:
        print(f'Что то пошло не так!')
        sys.exit(1)

    user_interface = threading.Thread(target=user_interactive, args=(s, username, resource_lock))
    # user_interface.daemon = True
    user_interface.start()

    receiver = threading.Thread(target=message_from_server, args=(s,))
    # receiver.daemon = True
    receiver.start()


if __name__ == '__main__':
    main()
