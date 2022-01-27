import ipaddress
from _socket import gethostbyname
from subprocess import Popen, PIPE

ip_list = ['0.0.0.0', '456.0.0.1', 'ya.ru', 'ab57.ru']


def host_ping(ip_str_list):
    for ip_str_adr in ip_str_list:
        p = Popen(['ping', '-c', '1', ip_str_adr], stdout=PIPE, stderr=PIPE)   #объект не принимает объект ipadress,только строку
        out = p.stdout.read()
        if out:
            try:
                ip_adr = ipaddress.ip_address(ip_str_adr)
            except ValueError:
                ip_adr = ipaddress.ip_address(gethostbyname(f'{ip_str_adr}'))
            print(f'Узел {ip_adr} доступен')
        else:
            print(f'Узел {ip_str_adr} недоступен')

host_ping(ip_list)