import socket
import time
import threading
import logs.config_client_log
from common.utils import *
from common.variables import *
from descriptors import Port
from errors import IncorrectDataRecivedError, ReqFieldMissingError, ServerError
from decos import log

# Инициализация клиентского логера
from metaclasses import ClientMaker, ClientBaseMaker

logger = logging.getLogger('client')


class ClientSender(threading.Thread, metaclass=ClientMaker):
    def __init__(self, account_name, sock):
        self.account_name = account_name
        self.sock = sock
        super().__init__()

    # Функция создаёт словарь с сообщением о выходе.
    @log
    def create_exit_message(self):
        return {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.account_name
        }


    @log
    # Функция запрашивает кому отправить сообщение и само сообщение, и отправляет полученные данные на сервер.
    def create_message(self):
        to = input('Введите получателя сообщения: ')
        message = input('Введите сообщение для отправки: ')
        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.account_name,
            DESTINATION: to,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        logger.debug(f'Сформирован словарь сообщения: {message_dict}')
        try:
            send_message(self.sock, message_dict)
            logger.info(f'Отправлено сообщение для пользователя {to}')
        except:
            logger.critical('Потеряно соединение с сервером.')
            exit(1)

    @log
    # Функция взаимодействия с пользователем, запрашивает команды, отправляет сообщения
    def run(self):
        self.print_help()
        while True:
            command = input('Введите команду: ')
            if command == 'message':
                self.create_message()
            elif command == 'help':
                self.print_help()
            elif command == 'exit':
                send_message(self.sock, self.create_exit_message())
                print('Завершение соединения.')
                logger.info('Завершение работы по команде пользователя.')
                # Задержка неоходима, чтобы успело уйти сообщение о выходе
                time.sleep(0.5)
                break
            else:
                print('Команда не распознана, попробойте снова. help - вывести поддерживаемые команды.')

    # Функция выводящяя справку по использованию.
    def print_help(self):
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')


# Класс-приёмник сообщений с сервера. Принимает сообщения, выводит в консоль.
class ClientReader(threading.Thread, metaclass=ClientMaker):
    def __init__(self, account_name, sock):
        self.account_name = account_name
        self.sock = sock
        super().__init__()

    @log
    # Функция - обработчик сообщений других пользователей, поступающих с сервера.
    def run(self):
        while True:
            try:
                message = get_message(self.sock)
                if ACTION in message and message[ACTION] == MESSAGE and SENDER in message and DESTINATION in message \
                        and MESSAGE_TEXT in message and message[DESTINATION] == self.account_name:
                    print(f'\nПолучено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                    logger.info(f'Получено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                else:
                    logger.error(f'Получено некорректное сообщение с сервера: {message}')
            except IncorrectDataRecivedError:
                logger.error(f'Не удалось декодировать полученное сообщение.')
            except (OSError, ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
                logger.critical(f'Потеряно соединение с сервером.')
                break


class ClientBase(metaclass=ClientBaseMaker):
    port = Port()

    def __init__(self):
        # Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию.
        self.addr, self.port, self.client_name = arg_parser(False)
        # Если имя пользователя не было задано, необходимо запросить пользователя.
        if self.client_name is None:
            self.client_name = input('Введите имя пользователя: ')

    # Функция разбирает ответ сервера на сообщение о присутствии, возращает 200 если все ОК или генерирует исключение при\
    # ошибке.
    @log
    def process_response_ans(self, message):
        logger.debug(f'Разбор приветственного сообщения от сервера: {message}')
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return '200 : OK'
            elif message[RESPONSE] == 400:
                raise ServerError(f'400 : {message[ERROR]}')
        raise ReqFieldMissingError(RESPONSE)

    # Функция генерирует запрос о присутствии клиента
    @log
    def create_presence(self):
        out = {
            ACTION: PRESENCE,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: self.client_name
            }
        }
        logger.debug(f'Сформировано {PRESENCE} сообщение для пользователя {self.client_name}')
        return out

    def run(self):
        # Сообщаем о запуске
        print('Консольный месседжер. Клиентский модуль.')

        logger.info(
            f'Запущен клиент с парамертами: адрес сервера: {self.addr} , порт: {self.port}, '
            f'имя пользователя: {self.client_name}')

        # Инициализация сокета и сообщение серверу о нашем появлении
        try:
            transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            transport.connect((self.addr, self.port))
            send_message(transport, self.create_presence())
            answer = self.process_response_ans(get_message(transport))
            logger.info(f'Установлено соединение с сервером. Ответ сервера: {answer}')
            print(f'Установлено соединение с сервером для пользователя: {self.client_name}')
        except json.JSONDecodeError:
            logger.error('Не удалось декодировать полученную Json строку.')
            exit(1)
        except ServerError as error:
            logger.error(f'При установке соединения сервер вернул ошибку: {error.text}')
            exit(1)
        except ReqFieldMissingError as missing_error:
            logger.error(f'В ответе сервера отсутствует необходимое поле {missing_error.missing_field}')
            exit(1)
        except (ConnectionRefusedError, ConnectionError):
            logger.critical(
                f'Не удалось подключиться к серверу {self.addr}:{self.port}, '
                f'конечный компьютер отверг запрос на подключение.')
            exit(1)
        else:
            # Если соединение с сервером установлено корректно, запускаем клиенский процесс приёма сообщний

            receiver = ClientReader(self.client_name, transport)
            receiver.daemon = True
            receiver.start()

            # затем запускаем отправку сообщений и взаимодействие с пользователем.
            user_interface = ClientSender(self.client_name, transport)
            user_interface.daemon = True
            user_interface.start()
            logger.debug('Запущены процессы')

            # Watchdog основной цикл, если один из потоков завершён, то значит или потеряно соединение или пользователь
            # ввёл exit. Поскольку все события обработываются в потоках, достаточно просто завершить цикл.
            while True:
                time.sleep(1)
                if receiver.is_alive() and user_interface.is_alive():
                    continue
                break


def main():
    client = ClientBase()
    client.run()

if __name__ == '__main__':
    main()
