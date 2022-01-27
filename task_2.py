from task_1 import host_ping


some_ip = '198.162.10.24'


def host_range_ping(ip_str):
    ip_range = ip_str.split('.')[-1]
    net = '.'.join(ip_str.split('.')[:-1])
    ip_list = [f'{net}.{i}' for i in range(int(ip_range))]
    return ip_list


host_ping(host_range_ping(some_ip))