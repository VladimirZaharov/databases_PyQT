import datetime
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import mapper, sessionmaker


class ClientDatabase:
    class Contacts:
        def __init__(self, name, time, friend):
            self.id = None
            self.name = name
            self.time = time
            self.friend = friend

    class Messages:
        def __init__(self, sender, recipient, message, time, is_in_contacts):
            self.id = None
            self.sender = sender
            self.recipient = recipient
            self.message = message
            self.time = time
            self.is_in_contacts = is_in_contacts

    def __init__(self, name):
        self.engine = create_engine(f'sqlite:///{name}_database.db3', echo=False)
        self.metadata = MetaData()
        clients_table = Table('Contacts', self.metadata,
                              Column('id', Integer, primary_key=True),
                              Column('name', String),
                              Column('time', DateTime),
                              Column('friend', Boolean),
                              )
        messages_table = Table('Messages', self.metadata,
                                      Column('id', Integer, primary_key=True),
                                      Column('sender', String),
                                      Column('recipient', String),
                                      Column('message', String),
                                      Column('time', DateTime),
                                      Column('is_in_contacts', Boolean),
                                      )

        self.metadata.create_all(self.engine)
        mapper(self.Contacts, clients_table)
        mapper(self.Messages, messages_table)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def add_message(self, sender, recipient, message):
        if sender == 'Me':
            name = recipient
        else:
            name = sender
        f = self.session.query(self.Contacts)
        in_contacts = self.session.query(self.Contacts).filter_by(name=name).count()
        if in_contacts:
            is_in_contacts = True
        else:
            is_in_contacts = False
        current_message = self.Messages(sender, recipient, message, datetime.datetime.now(), is_in_contacts)
        self.session.add(current_message)
        self.session.commit()

    def make_friend(self, name):
        friend = input(f'Сделать {name} другом? (y/n): ')
        if friend == 'y':
            self.is_friend = True
        elif friend == 'n':
            self.is_friend = False
        else:
            print('Введите "y" - если сделать, "n" - если нет')
            self.make_friend(name)

    def add_contact(self, name):
        self.make_friend(name)
        new_contact = self.Contacts(name, datetime.datetime.now(), self.is_friend)
        self.session.add(new_contact)
        self.session.commit()

    def del_contact(self, name):
        contact = self.session.query(self.Contacts).filter_by(name=name).first()
        if contact is None:
            print(f'{name} нет в списке ваших контактов')
        else:
            self.session.delete(contact)
            self.session.commit()

    def get_contacts(self):
        contacts = self.session.query(self.Contacts)
        return {client.name: ("" if client.friend is False else "(friend)") for client in contacts}