import configparser
import os
import socket
import select
import threading
import time
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer
from server_gui import MainWindow, gui_create_model, HistoryWindow, create_stat_model, ConfigWindow
from PyQt5.QtGui import QStandardItemModel, QStandardItem
import logs.config_server_log
from descriptors import Port
from errors import IncorrectDataRecivedError
from common.variables import *
from common.utils import *
from decos import log
from metaclasses import ServerMaker
from server_database import ServerDatabase


# Инициализация логирования сервера.

logger = logging.getLogger('server')

new_connection = False
conflag_lock = threading.Lock()

class Server(threading.Thread, metaclass=ServerMaker):
    port = Port()

    def __init__(self, port, ip_addr, database):
        # Параметры подключения
        # Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию.
        self.addr = ip_addr
        self.port = port
        # Список подключённых клиентов.
        self.clients = []

        # Список сообщений на отправку.
        self.messages = []

        # Словарь содержащий сопоставленные имена и соответствующие им сокеты.
        self.names = dict()

        # Подключаем базу.
        self.database = database
        super().__init__()


    # Обработчик сообщений от клиентов, принимает словарь - сообщение от клиента, проверяет корректность, отправляет
    #     словарь-ответ в случае необходимости.
    @log
    def process_client_message(self, message, client):
        logger.debug(f'Разбор сообщения от клиента : {message}')
        # Если это сообщение о присутствии, принимаем и отвечаем
        if ACTION in message and message[ACTION] == PRESENCE and TIME in message and USER in message:
            # Если такой пользователь ещё не зарегистрирован, регистрируем, иначе отправляем ответ и завершаем соединение.
            if message[USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[message[USER][ACCOUNT_NAME]] = client
                ip_adr, port = client.getpeername()
                self.database.client_login(message[USER][ACCOUNT_NAME], ip_adr, port)
                send_message(client, RESPONSE_200)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Имя пользователя уже занято.'
                send_message(client, response)
                self.clients.remove(client)
                client.close()
            return
        # Если это сообщение, то добавляем его в очередь сообщений. Ответ не требуется.
        elif ACTION in message and message[ACTION] == MESSAGE and DESTINATION in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message:
            self.messages.append(message)
            return
        # Если клиент выходит
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
            self.database.client_logout(message[ACCOUNT_NAME])
            self.clients.remove(self.names[message[ACCOUNT_NAME]])
            self.names[message[ACCOUNT_NAME]].close()
            del self.names[message[ACCOUNT_NAME]]
            return
        elif ACTION in message and message[ACTION] == GET_CLIENTS and ACCOUNT_NAME in message:
            client_list = self.database.get_clients()
            response = {GET_CLIENTS: client_list}
            send_message(client, response)
        # Иначе отдаём Bad request
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            send_message(client, response)
            return


    @log
    # Функция адресной отправки сообщения определённому клиенту. Принимает словарь сообщение, список зарегистрированых
    # пользователей и слушающие сокеты. Ничего не возвращает.
    def process_message(self, message):
        if message[DESTINATION] in self.names and self.names[message[DESTINATION]] in self.send_data_lst:
            send_message(self.names[message[DESTINATION]], message)
            self.database.client_send_message(message[SENDER], message[DESTINATION], message[MESSAGE_TEXT])
            logger.info(f'Отправлено сообщение пользователю {message[DESTINATION]} от пользователя {message[SENDER]}.')
        elif message[DESTINATION] in self.names and self.names[message[DESTINATION]] not in self.send_data_lst:
            raise ConnectionError
        else:
            logger.error(
                f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере, отправка сообщения невозможна.')

    def init_socket(self):
        logger.info(
            f'Запущен сервер, порт для подключений: {self.port} , '
            f'адрес с которого принимаются подключения: {self.addr}. '
            f'Если адрес не указан, принимаются соединения с любых адресов.')
        # Готовим сокет
        self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.transport.bind((self.addr, self.port))
        self.transport.settimeout(0.5)

        # Слушаем порт
        self.transport.listen(MAX_CONNECTIONS)

    def run(self):
        # Инициализация Сокета
        self.init_socket()

        while True:
            # Ждём подключения, если таймаут вышел, ловим исключение.
            try:
                client, client_address = self.transport.accept()
            except OSError:
                pass
            else:
                logger.info(f'Установлено соедение с ПК {client_address}')
                self.clients.append(client)

            self.recv_data_lst = []
            self.send_data_lst = []
            err_lst = []
            # Проверяем на наличие ждущих клиентов
            try:
                if self.clients:
                    self.recv_data_lst, self.send_data_lst, err_lst = select.select(self.clients, self.clients, [], 0)
            except OSError:
                pass

            # принимаем сообщения и если ошибка, исключаем клиента.
            if self.recv_data_lst:
                for client_with_message in self.recv_data_lst:
                    try:
                        self.process_client_message(get_message(client_with_message), client_with_message)
                    except Exception as e:
                        print(e)
                        logger.info(f'Клиент {client_with_message.getpeername()} отключился от сервера.')
                        self.clients.remove(client_with_message)

            # Если есть сообщения, обрабатываем каждое.
            for i in self.messages:
                try:
                    self.process_message(i)
                except Exception as e:
                    print(e)
                    logger.info(f'Связь с клиентом с именем {i[DESTINATION]} была потеряна')
                    self.clients.remove(self.names[i[DESTINATION]])
                    del self.names[i[DESTINATION]]
            self.messages.clear()


def main():
    config = configparser.ConfigParser()

    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f"{dir_path}/{'server.ini'}")

    ip_addr, port, temp_arg = arg_parser(config['SETTINGS']['Default_port'],
                                         config['SETTINGS']['Listen_Address'])

    database = ServerDatabase(os.path.join(
            config['SETTINGS']['Database_path'],
            config['SETTINGS']['Database_file']))
    # Основной цикл программы сервера
    server = Server(port, ip_addr, database)
    server.deamon = True
    server.start()

    # server_app = QApplication(sys.argv)
    # main_window = MainWindow()
    #
    # # Инициализируем параметры в окна
    # main_window.statusBar().showMessage('Server Working')
    # main_window.active_clients_table.setModel(gui_create_model(database))
    # main_window.active_clients_table.resizeColumnsToContents()
    # main_window.active_clients_table.resizeRowsToContents()
    #
    # # Функция, обновляющая список подключённых, проверяет флаг подключения, и
    # # если надо обновляет список
    # def list_update():
    #     global new_connection
    #     if new_connection:
    #         main_window.active_clients_table.setModel(
    #             gui_create_model(database))
    #         main_window.active_clients_table.resizeColumnsToContents()
    #         main_window.active_clients_table.resizeRowsToContents()
    #         with conflag_lock:
    #             new_connection = False
    #
    # # Функция, создающая окно со статистикой клиентов
    # def show_statistics():
    #     global stat_window
    #     stat_window = HistoryWindow()
    #     stat_window.history_table.setModel(create_stat_model(database))
    #     stat_window.history_table.resizeColumnsToContents()
    #     stat_window.history_table.resizeRowsToContents()
    #     stat_window.show()
    #
    # # Функция создающяя окно с настройками сервера.
    # def server_config():
    #     global config_window
    #     # Создаём окно и заносим в него текущие параметры
    #     config_window = ConfigWindow()
    #     config_window.db_path.insert(config['SETTINGS']['Database_path'])
    #     config_window.db_file.insert(config['SETTINGS']['Database_file'])
    #     config_window.port.insert(config['SETTINGS']['Default_port'])
    #     config_window.ip.insert(config['SETTINGS']['Listen_Address'])
    #     config_window.save_btn.clicked.connect(save_server_config)
    #
    # # Функция сохранения настроек
    # def save_server_config():
    #     global config_window
    #     message = QMessageBox()
    #     config['SETTINGS']['Database_path'] = config_window.db_path.text()
    #     config['SETTINGS']['Database_file'] = config_window.db_file.text()
    #     try:
    #         port = int(config_window.port.text())
    #     except ValueError:
    #         message.warning(config_window, 'Ошибка', 'Порт должен быть числом')
    #     else:
    #         config['SETTINGS']['Listen_Address'] = config_window.ip.text()
    #         if 1023 < port < 65536:
    #             config['SETTINGS']['Default_port'] = str(port)
    #             print(port)
    #             with open('server.ini', 'w') as conf:
    #                 config.write(conf)
    #                 message.information(
    #                     config_window, 'OK', 'Настройки успешно сохранены!')
    #         else:
    #             message.warning(
    #                 config_window,
    #                 'Ошибка',
    #                 'Порт должен быть от 1024 до 65536')
    #
    # # Таймер, обновляющий список клиентов 1 раз в секунду
    # timer = QTimer()
    # timer.timeout.connect(list_update)
    # timer.start(1000)
    #
    # # Связываем кнопки с процедурами
    # main_window.refresh_button.triggered.connect(list_update)
    # main_window.show_history_button.triggered.connect(show_statistics)
    # main_window.config_btn.triggered.connect(server_config)
    #
    # # Запускаем GUI
    # server_app.exec_()


if __name__ == '__main__':
    main()
