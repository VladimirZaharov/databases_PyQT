from subprocess import Popen, PIPE


def client_num_run():
    number_apps = int(input('Введите количество требуемых приложений: '))
    type_apps = input('Тип приложения("send" или "listen"): ')
    for i in range(number_apps):
        client_app = Popen(['python3', 'client.py', '-m', type_apps], stdout=PIPE, stderr=PIPE)

