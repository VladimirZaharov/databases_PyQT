import configparser
import os
import socket
import time
import threading
import logs.config_client_log
from client_database import ClientDatabase
from common.utils import *
from common.variables import *
from descriptors import Port
from errors import IncorrectDataRecivedError, ReqFieldMissingError, ServerError
from decos import log

# Инициализация клиентского логера
from metaclasses import ClientMaker, ClientBaseMaker

logger = logging.getLogger('client')

sock_lock = threading.Lock()
database_lock = threading.Lock()

registered_clients = []

class ClientSender(threading.Thread, metaclass=ClientMaker):
    def __init__(self, account_name, sock, database):
        self.database = database
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
            self.database.add_message('Me', to, message)
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
            match command:
                case 'message':
                    self.create_message()
                    time.sleep(1)
                case 'help':
                    self.print_help()
                    time.sleep(1)
                case 'contacts':
                    self.contacts_loop()
                    time.sleep(1)
                case 'exit':
                    send_message(self.sock, self.create_exit_message())
                    print('Завершение соединения.')
                    logger.info('Завершение работы по команде пользователя.')
                    # Задержка неоходима, чтобы успело уйти сообщение о выходе
                    time.sleep(0.5)
                    break

    def print_contacts(self, contacts):
        if contacts == {}:
            return 'У Вас нет добавленных контактов'
        else:
            contacts_str = ''
            for name, is_friend in contacts.items():
                contacts_str += f' {name} {is_friend} |'
            return contacts_str

    def contacts_loop(self):
        while True:
            print('Вы находитесь в меню работы с контатами!')
            print("help - вывести подсказки по командам")
            print('contacts - вывести список зарегистрированных клиентов и контактов')
            print('add - добавить клиента в контакт')
            print('del - удалить клиента из контактов')
            print('exit - выйти в главное меню')
            command = input('Введите команду: ')
            match command:
                case 'help':
                    continue
                case 'contacts':
                    with sock_lock:
                        send_message(self.sock, self.get_clients_message())
                    time.sleep(1)
                    with database_lock:
                        contacts = self.database.get_contacts()
                        print(f'Ваши контакты: {self.print_contacts(contacts)}')

                    time.sleep(1)
                case 'add':
                    with sock_lock:
                        send_message(self.sock, self.get_clients_message())
                    time.sleep(1)
                    name_to_add = input('Введите имя из списка для добавления: ')
                    if name_to_add in registered_clients:
                        self.database.add_contact(name_to_add)
                        print(f'{name_to_add} добавлен')
                    else:
                        print(f'{name_to_add} не зарегистрирован в системе')
                    time.sleep(1)

                case 'del':
                    with database_lock:
                        contacts = self.database.get_contacts()
                        print(self.print_contacts(contacts))
                    time.sleep(0.5)
                    name_to_del = input('Введите имя из списка для удаления: ')
                    if name_to_del in contacts:
                        self.database.del_contact(name_to_del)
                        print(f'{name_to_del} удален')
                    else:
                        print(f'{name_to_del} не зарегистрирован в контактах')
                    time.sleep(1)
                case 'exit':
                    self.print_help()
                    break

    def get_clients_message(self):
        return {
            ACTION: GET_CLIENTS,
            TIME: time.time(),
            ACCOUNT_NAME: self.account_name
        }


    # Функция выводящяя справку по использованию.
    def print_help(self):
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('help - вывести подсказки по командам')
        print('contacts - вывести список клиентов, клиентов в списке контактов')
        print('exit - выход из программы')
        print('')


# Класс-приёмник сообщений с сервера. Принимает сообщения, выводит в консоль.
class ClientReader(threading.Thread, metaclass=ClientMaker):
    def __init__(self, account_name, sock, database):
        self.database = database
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
                    self.database.add_message(message[SENDER], 'Me', message[MESSAGE_TEXT])
                    print(f'\nПолучено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                    logger.info(f'Получено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                elif GET_CLIENTS in message:
                    registered_clients.clear()
                    for clients in message[GET_CLIENTS]:
                        registered_clients.append(clients)
                    print(f'Зарегистрированные клиенты: {registered_clients}')
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
        config = configparser.ConfigParser()

        dir_path = os.path.dirname(os.path.realpath(__file__))
        config.read(f"{dir_path}/{'client.ini'}")
        # Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию.
        self.addr, self.port, self.client_name = arg_parser(config['SETTINGS']['Default_port'],
                                                            config['SETTINGS']['Listen_Address'])
        # Если имя пользователя не было задано, необходимо запросить пользователя.
        if self.client_name is None:
            self.client_name = input('Введите имя пользователя: ')
        self.database = ClientDatabase(self.client_name)

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

            receiver = ClientReader(self.client_name, transport, self.database)
            receiver.daemon = True
            receiver.start()

            # затем запускаем отправку сообщений и взаимодействие с пользователем.
            user_interface = ClientSender(self.client_name, transport, self.database)
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
