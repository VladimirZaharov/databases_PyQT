import ipaddress
from _socket import gethostbyname
from itertools import zip_longest
from subprocess import Popen, PIPE

from tabulate import tabulate


def host_range_ping_tab(ip_str_list):
    ip_list_not_av =[]
    ip_list_av = []
    for ip_str_adr in ip_str_list:
        p = Popen(['ping', '-c', '1', ip_str_adr], stdout=PIPE, stderr=PIPE)   #объект не принимает объект ipadress,только строку
        out = p.stdout.read()
        if out:
            try:
                ip_adr = ipaddress.ip_address(ip_str_adr)
            except ValueError:
                ip_adr = ipaddress.ip_address(gethostbyname(f'{ip_str_adr}'))
            ip_list_av.append(ip_str_adr)
        else:
            ip_list_not_av.append(ip_str_adr)
    ip_list_sorted = zip_longest(ip_list_av, ip_list_not_av)
    headers = ['Reachable', 'Unreachble']
    print(tabulate(ip_list_sorted, headers))

ip_list = ['0.0.0.0', '456.0.0.1', 'ya.ru', 'ab57.ru']
host_range_ping_tab(ip_list)