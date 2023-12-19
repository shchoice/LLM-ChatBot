from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, Float, Text

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String, default='default')
    user_total_cost = Column(Float, default=0.0)


class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey('rooms.id', ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey('users.id'))
    user_message = Column(String)
    chatbot_message = Column(String)
    messages = Column(Text)
    model_name = Column(String)
    total_tokens = Column(Integer)
    cost = Column(Float)


class Room(Base):
    __tablename__ = 'rooms'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'))  # 사용자 ID 외래 키 추가
    room_total_cost = Column(Float, default=0.0)

