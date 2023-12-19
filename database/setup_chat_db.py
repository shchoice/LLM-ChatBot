import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Room, Message, User

class ChatDatabase:
    def __init__(self, db_file):
        self.engine = create_engine(f'sqlite:///{db_file}', echo=False)
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)

    def get_session(self):
        return self.Session()

    def add_message(self, room_name, user_id, user_name, user_message, chatbot_message, messages, model_name, total_tokens, cost):
        session = self.get_session()

        room = session.query(Room).filter_by(name=room_name, user_id=user_id).first()
        if room is None:
            room = Room(
                name=room_name,
                user_id=user_id,
                room_total_cost=0.0
            )
            session.add(room)
            session.commit()

        user = session.query(User).filter_by(name=user_name).first()
        if user is None:
            user = User(
                name=user_name,
                user_total_cost=0.0
            )
            session.add(user)
            session.commit()

        message = Message(
            room_id=room.id,
            user_id=user_id,
            user_message=user_message,
            chatbot_message=chatbot_message,
            messages=messages,
            model_name=model_name,
            total_tokens=total_tokens,
            cost=cost
        )
        session.add(message)

        room.room_total_cost += cost
        user.user_total_cost += cost

        session.commit()

    def load_users(self):
        session = self.get_session()
        users = session.query(User).all()
        users_data = {user.id: user.name for user in users}
        return users_data

    def load_chat_rooms(self, user_id):
        session = self.get_session()
        rooms = session.query(Room).filter_by(user_id=user_id).all()
        room_list = []
        chat_rooms_data = {}
        users_data = self.load_users()
        for room in rooms:
            room_list.append(room.name)
            messages = session.query(Message).filter_by(room_id=room.id).order_by(Message.id).all()
            chat_history = json.loads(messages[-1].messages)
            chatbot_message_list = []
            user_message_list = []
            model_names = []
            total_tokens_list = []
            costs = []
            for message in messages:
                chatbot_message_list.append(message.chatbot_message)
                user_message_list.append(message.user_message)
                model_names.append(message.model_name)
                total_tokens_list.append(message.total_tokens)
                costs.append(message.cost)
            chat_rooms_data[room.name] = {
                'chatbot_message': chatbot_message_list,
                'user_message': user_message_list,
                'messages': chat_history,
                'total_cost': room.room_total_cost,
                'model_name': model_names,
                'total_tokens': total_tokens_list,
                'cost': costs,
            }

        return room_list, chat_rooms_data, users_data

    def delete_room_and_messages(self, room):
        session = self.get_session()
        room = session.query(Room).filter_by(name=room).first()
        if room:
            session.query(Message).filter_by(room_id=room.id).delete()
        else:
            print("채팅방이 존재하지 않습니다.")
            return
        session.delete(room)
        session.commit()

    def user_login(self, user_name: str):
        session = self.get_session()
        try:
            user = session.query(User).filter_by(name=user_name).first()
            if user is None:
                user = User(name=user_name)
                session.add(user)
                session.commit()
                user = session.query(User).filter_by(name=user_name).first()
            return user
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_default_user(self):
        session = self.get_session()
        default_user = session.query(User).filter_by(name='default').first()
        if default_user is None:
            default_user = User(name='default')
            session.add(default_user)
            session.commit()
        return default_user
