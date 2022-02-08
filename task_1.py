import ipaddress
import threading
from _socket import gethostbyname
from subprocess import Popen, PIPE


def host_ping(ip_str):
    print(f'узел {ip_str} проверяется')
    p = Popen(['ping', '-c', '1', ip_str], stdout=PIPE, stderr=PIPE)   #объект не принимает объект ipadress,только строку
    out = p.stdout.read()
    if out:
        try:
            ip_adr = ipaddress.ip_address(ip_str)
        except ValueError:
            ip_adr = ipaddress.ip_address(gethostbyname(f'{ip_str}'))
        print(f'Узел {ip_adr} доступен')
    else:
        print(f'Узел {ip_str} недоступен')


def host_ping_lst(ip_list):
    for ip_str in ip_list:
        threading.Thread(target=host_ping, args=(ip_str,)).start()


if __name__ == "__main__":
    ip_list = ['0.0.0.0', '456.0.0.1', 'ya.ru', 'ab57.ru']
    host_ping_lst(ip_list)
