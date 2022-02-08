import logging
import os
import traceback


def log_decorator(func):
    def log_dec(*args,**kwargs):
        res = func(*args, **kwargs)
        logger = logging.getLogger('messenger.function_usage')
        formatter = logging.Formatter("%(asctime)s  %(message)-10s")

        PATH = os.path.dirname(__file__)
        PATH = os.path.join(PATH, 'func_usage.log')

        server_file_handler = logging.FileHandler(PATH, encoding='utf-8')
        server_file_handler.setLevel(logging.DEBUG)
        server_file_handler.setFormatter(formatter)
        logger.addHandler(server_file_handler)
        logger.setLevel(logging.DEBUG)
        logger.info(f'Функция {func.__name__} вызвана из функции '
                    f'{"".join(traceback.format_stack()[0].strip().split()[-1])} '
                    f'модуля {traceback.format_stack()[1].strip().split()[1].split("/")[-1]}')
        return res
    return log_dec
