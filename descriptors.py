import logging
server_logger = logging.getLogger('server')
client_logger = logging.getLogger('client')

# Дескриптор для описания порта:
class Port:
    def __set__(self, instance, value):
        if 1023 < value < 65536:
            instance.__dict__[self.name] = value
        else:
            server_logger.critical(
                f'Попытка запуска {self.owner} с указанием неподходящего порта {value}. Допустимы адреса с 1024 до 65535.')
            exit(1)

    def __set_name__(self, owner, name):
        self.name = name
        self.owner = owner.__name__



