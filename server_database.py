import datetime
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import mapper, sessionmaker


class ServerDatabase:
    class Clients:
        def __init__(self, name, time):
            self.id = None
            self.name = name
            self.first_login_time = time
            self.online = True

    class LoginHistory:
        def __init__(self, id, time, port, ip_adr):
            self.id = None
            self.client_id = id
            self.login_time = time
            self.port = port
            self.ip = ip_adr

    class MessageHistory:
        def __init__(self, sender_id, recipient_id, message, time):
            self.id = None
            self.sender_id = sender_id
            self.recipient_id = recipient_id
            self.message = message
            self.time = time

    def __init__(self, path):
        self.engine = create_engine(f'sqlite:///{path}', echo=False)
        self.metadata = MetaData()
        clients_table = Table('Clients', self.metadata,
                              Column('id', Integer, primary_key=True),
                              Column('name', String),
                              Column('first_login_time', DateTime),
                              Column('online', Boolean),
                              )
        login_history_table = Table('Login_history', self.metadata,
                                    Column('id', Integer, primary_key=True),
                                    Column('client_id', ForeignKey('Clients.id')),
                                    Column('login_time', DateTime),
                                    Column('port', Integer),
                                    Column('ip', String),
                                    )
        message_history_table = Table('Message_history', self.metadata,
                                      Column('id', Integer, primary_key=True),
                                      Column('sender_id', ForeignKey('Clients.id')),
                                      Column('recipient_id', ForeignKey('Clients.id')),
                                      Column('message', String),
                                      Column('time', DateTime),
                                      )

        self.metadata.create_all(self.engine)
        mapper(self.Clients, clients_table)
        mapper(self.LoginHistory, login_history_table)
        mapper(self.MessageHistory, message_history_table)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def client_login(self, name, ip, port):
        client = self.session.query(self.Clients).filter_by(name=name)
        if not client.count():
            client = self.Clients(name, datetime.datetime.now())
            self.session.add(client)
            self.session.commit()
            client = self.session.query(self.Clients).filter_by(name=name)
        client = client.first()
        client.online = True
        current_client = self.LoginHistory(client.id, datetime.datetime.now(), port, ip)
        self.session.add(current_client)
        self.session.commit()

    def get_clients(self):
        clients = self.session.query(self.Clients.name).all()
        return [client[0] for client in clients]

    def client_send_message(self, sender, recipient, message):
        client_sender = self.session.query(self.Clients).filter_by(name=sender)
        client_sender = client_sender.first()
        client_recipient = self.session.query(self.Clients).filter_by(name=recipient)
        client_recipient = client_recipient.first()
        current_message = self.MessageHistory(client_sender.id, client_recipient.id, message, datetime.datetime.now())
        self.session.add(current_message)
        self.session.commit()

    def client_logout(self, name):
        client = self.session.query(self.Clients).filter_by(name=name).first()
        client.online = False
        self.session.commit()


if __name__ == '__main__':
    pass
