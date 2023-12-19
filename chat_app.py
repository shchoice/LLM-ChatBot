import json
import time
from typing import List

import numpy as np
import requests
from openai import OpenAI
import streamlit as st

from database.setup_chat_db import ChatDatabase

BASE_URL ='http://localhost:8000'
CHATGPT_3_API_URL = BASE_URL + '/chat/gpt3'
CHATGPT_4_API_URL = BASE_URL + '/chat/gpt4'

SYSTEM_MSG = "You are a helpful assistant"

class ChatBotApp:
    def __init__(self):
        self.client = OpenAI()
        self.room_name = None
        self.model_name = None
        self.temperature = 0.2
        self.max_tokens = 256
        self.counter_placeholder = None

        database = 'chatbot.db'
        self.chat_bot_db = ChatDatabase(database)
        self.current_user = self.chat_bot_db.user_login('default')

        self.initialize_session_state()
        self.setup_ui()


    def initialize_session_state(self):
        user_name = self.current_user.name
        user_id = self.current_user.id

        if user_name not in st.session_state:
            st.session_state[user_name] = {}
            st.session_state[user_name]['chat_rooms'] = {}

        rooms, chat_rooms_data, users_data = self.chat_bot_db.load_chat_rooms(user_id)
        if chat_rooms_data:
            for room in rooms:
                st.session_state[user_name]['chat_rooms'][room] = chat_rooms_data.get(room)
                st.session_state['users'] = users_data

    def initialize_chat_room_session_state(self, room_name):
        user_name = self.current_user.name
        st.session_state[user_name]['chat_rooms'][room_name] = {}
        st.session_state[user_name]['chat_rooms'][room_name]['chatbot_message'] = []
        st.session_state[user_name]['chat_rooms'][room_name]['user_message'] = []
        st.session_state[user_name]['chat_rooms'][room_name]['messages'] = []
        st.session_state[user_name]['chat_rooms'][room_name]['model_name'] = []
        st.session_state[user_name]['chat_rooms'][room_name]['cost'] = []
        st.session_state[user_name]['chat_rooms'][room_name]['total_tokens'] = []
        st.session_state[user_name]['chat_rooms'][room_name]['total_cost'] = 0.0

    def setup_ui(self):
        # Setting page title and header
        st.set_page_config(page_title="Seohwan Choi's ChatGPT", page_icon=":robot_face:")
        st.markdown("<h1 style='text-align: center;'>Seohwan Choi's ChatGPT🤩</h1>", unsafe_allow_html=True)
        is_first: bool = self.sidebar_setup()
        if not is_first and self.room_name:
            self.main_chat_window()

    def sidebar_setup(self):
        def login_setting_setup():
            with st.sidebar:
                # 로그인 상태를 확인하는 세션 상태 변수 추가
                if 'logged_in' not in st.session_state:
                    st.session_state['logged_in'] = False

                # 로그인 상태가 아닐 때만 로그인 버튼과 로그인 필드를 표시
                if not st.session_state['logged_in']:
                    user_name = st.text_input("사용자 이름을 입력하세요.", key="login_username")
                    if st.button('로그인'):
                        if user_name:
                            self.login(user_name)
                            st.session_state['logged_in'] = True  # 로그인 상태를 True로 변경
                            st.rerun()

                # 로그인 상태일 때만 로그아웃 버튼을 표시
                if st.session_state['logged_in']:
                    if st.button("로그아웃"):
                        self.logout()
                        st.session_state['logged_in'] = False  # 로그아웃 상태를 False로 변경


        def sidebar_chat_settings_setup():
            st.sidebar.title('채팅 설정')

            st.sidebar.markdown('<h4>Model</h4>', unsafe_allow_html=True)
            self.model_name = st.sidebar.selectbox(
                'Choose a Model:',
                ("gpt-3.5-turbo", "gpt-4", "beomi/KoAlpaca-Polyglot-12.8B", "beomi/LLaMA-2-ko-7b", "beomi/LLaMA-2-ko-13b")
            )

            st.sidebar.markdown('<h4>Temperature</h4>', unsafe_allow_html=True)
            temperature_range = np.round(np.arange(0, 2.1, 0.1), 1)
            self.temperature = st.sidebar.select_slider('Choose a number', options=temperature_range, value=0.2)

            st.sidebar.markdown('<h4>Maximum token length</h4>', unsafe_allow_html=True)
            max_tokens_range = np.arange(1, 4097, 1)
            self.max_tokens = int(st.sidebar.select_slider('Choose a number', options=max_tokens_range, value=256))

        def sidebar_chat_rooms_setup() -> bool:
            user_name = self.current_user.name
            st.sidebar.markdown('<hr>', unsafe_allow_html=True)
            st.sidebar.title('채팅방')
            with st.sidebar.form("new_room"):
                if 'create_room_clicked' in st.session_state and st.session_state['create_room_clicked']:
                    st.session_state['new_room_text'] = ""
                    st.session_state['create_room_clicked'] = False

                room_name = st.text_input("새로운 방을 만드세요", key='new_room_text', value=st.session_state.get('new_room_text', ''))
                if st.form_submit_button("채팅방 생성"):
                    st.session_state['create_room_clicked'] = True
                    if room_name.strip() != '' and room_name not in st.session_state[user_name]['chat_rooms']:
                        print("init new chat room")
                        self.initialize_chat_room_session_state(room_name)
                        st.rerun()
                    else:
                        st.warning('유효한 채팅방 이름을 입력해주세요.')

            if not room_name:
                if st.session_state[user_name]['chat_rooms'] == {}:
                    return True
            elif room_name:
                if st.session_state[user_name]['chat_rooms'][room_name] == {}:
                    return True
            room_selection = st.sidebar.radio("Select room", list(st.session_state[user_name]['chat_rooms'].keys()))
            if room_selection:
                self.room_name = room_selection

            return False

        def sidebar_chat_usage_setup():
            st.sidebar.markdown('<h4>Usage</h4>', unsafe_allow_html=True)
            self.counter_placeholder = st.sidebar.empty()
            self.update_total_cost()

            delete_button = st.sidebar.button("대화방 삭제")
            if delete_button:
                self.delete_session_state()

        login_setting_setup()
        sidebar_chat_settings_setup()
        is_first: bool = sidebar_chat_rooms_setup()
        if is_first is False:
            sidebar_chat_usage_setup()

        return is_first

    def delete_session_state(self):
        user_name = self.current_user.name
        room_name = self.room_name
        if room_name:
            self.chat_bot_db.delete_room_and_messages(room_name)
        del st.session_state[user_name]['chat_rooms'][room_name]
        self.room_name = None
        st.rerun()

    def update_total_cost(self):
        user_name = self.current_user.name
        room_name = self.room_name
        self.counter_placeholder.write(f"Total costs: ${st.session_state[user_name]['chat_rooms'][room_name]['total_cost']:.5f}")

    def main_chat_window(self):
        user_name = self.current_user.name
        room_name = self.room_name

        if room_name:
            st.subheader(f"대화방: {room_name}")
        if st.session_state[user_name]['chat_rooms'][room_name]['chatbot_message']:
            self.display_chat_history()
        if user_message := st.chat_input(""):
            if user_message:
                self.handle_user_message(user_message)

            with st.chat_message('user'):
                user_message = st.session_state[user_name]['chat_rooms'][room_name]["user_message"][-1]
                st.markdown(user_message)

            with st.chat_message('assistant'):
                message_placeholder = st.empty()
                full_response = ""
                for lines in st.session_state[user_name]['chat_rooms'][room_name]['chatbot_message'][-1].split('\n'):
                    for chunk in lines.split():
                        full_response += chunk + " "
                        time.sleep(0.05)
                        message_placeholder.markdown(full_response)
                st.write(
                    f"Model used: {st.session_state[user_name]['chat_rooms'][room_name]['model_name'][-1]} \t"
                    f"Number of tokens: {st.session_state[user_name]['chat_rooms'][room_name]['total_tokens'][-1]} \t"
                    f"Cost: ${st.session_state[user_name]['chat_rooms'][room_name]['cost'][-1]:.5f}"
                )

    def handle_user_message(self, user_message):
        room_name = self.room_name
        user_name = self.current_user.name

        chatbot_message, total_tokens, prompt_tokens, completion_tokens = self.generate_response(user_message)
        st.session_state[user_name]['chat_rooms'][room_name]['user_message'].append(user_message)
        st.session_state[user_name]['chat_rooms'][room_name]['chatbot_message'].append(chatbot_message)
        st.session_state[user_name]['chat_rooms'][room_name]['total_tokens'].append(total_tokens)
        st.session_state[user_name]['chat_rooms'][room_name]['model_name'].append(self.model_name)

        cost = (total_tokens * 0.002 / 1000) if self.model_name == "gpt-3.5-turbo"\
            else (prompt_tokens * 0.03 + completion_tokens * 0.06) / 1000
        st.session_state[user_name]['chat_rooms'][room_name]['cost'].append(cost)
        st.session_state[user_name]['chat_rooms'][room_name]['total_cost'] += cost
        self.update_total_cost()
        messages_json = json.dumps(st.session_state[user_name]['chat_rooms'][room_name]['messages'])
        # For Debug
        print(st.session_state[user_name]['chat_rooms'][room_name]['chatbot_message'])
        print(st.session_state[user_name]['chat_rooms'][room_name]['user_message'])
        print(st.session_state[user_name]['chat_rooms'][room_name]['messages'])
        print(st.session_state[user_name]['chat_rooms'][room_name]['model_name'])
        print(st.session_state[user_name]['chat_rooms'][room_name]['total_tokens'])
        print(st.session_state[user_name]['chat_rooms'][room_name]['cost'])
        print(st.session_state[user_name]['chat_rooms'][room_name]['total_cost'])
        print()

        self.chat_bot_db.add_message(
            room_name=room_name,
            user_id=self.current_user.id,
            user_name=user_name,
            user_message=user_message,
            chatbot_message=chatbot_message,
            messages=messages_json,
            model_name=self.model_name,
            total_tokens=total_tokens,
            cost=cost
        )

    def generate_response(self, prompt):
        room_name = self.room_name
        user_name = self.current_user.name

        st.session_state[user_name]['chat_rooms'][room_name]['messages'].append({"role": "user", "content": prompt})

        completion = self.request_chat_api(
            model=self.model_name,
            message=st.session_state[user_name]['chat_rooms'][room_name]['messages'], # 대화했던 모든 메세지가 함께 날아감
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

        chatbot_message = completion.get('message', None)
        total_tokens = completion.get('total_tokens', 0)
        prompt_tokens = completion.get('prompt_tokens', 0)
        completion_tokens = completion.get('completion_tokens', 0)

        st.session_state[user_name]['chat_rooms'][room_name]['messages'].append({"role": "assistant", "content": chatbot_message})
        return chatbot_message, total_tokens, prompt_tokens, completion_tokens

    def request_chat_api(self, model: str, message: List[st.chat_message], max_tokens: int = 128, temperature: float = 0.2) -> str:
        chat_api_url = self.get_model_url()

        response = requests.post(
            chat_api_url,
            json={
                "model": model,
                "message": message,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        response = response.json()
        return response
    def get_model_url(self):
        # "gpt-3.5-turbo", "gpt-4", "beomi/KoAlpaca-Polyglot-12.8B", "beomi/LLaMA-2-ko-7b", "beomi/LLaMA-2-ko-13b"
        model_name = self.model_name
        if model_name == 'gpt-3.5-turbo':
            return CHATGPT_3_API_URL
        elif model_name == 'gpt-4-1106-preview':
            return CHATGPT_4_API_URL

    def display_chat_history(self):
        room_name = self.room_name
        user_name = self.current_user.name

        for i, message in enumerate(st.session_state[user_name]['chat_rooms'][room_name]['messages']):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

                if (i+1) % 2 == 0:
                    st.write(
                        f"Model used: {st.session_state[user_name]['chat_rooms'][room_name]['model_name'][int(i/2)]}     "
                        f"Number of tokens: {st.session_state[user_name]['chat_rooms'][room_name]['total_tokens'][int(i/2)]}     "
                        f"Cost: ${st.session_state[user_name]['chat_rooms'][room_name]['cost'][int(i/2)]:.5f}"
                    )

    def login(self, user_name: str):
        user = self.chat_bot_db.user_login(user_name=user_name)
        self.current_user = user.name
        st.session_state['user_id'] = user.id
        st.session_state['user_name'] = user.name
        st.success(f'{user.name}으로 로그인 되었습니다.')

    def logout(self):
        default_user = self.chat_bot_db.get_default_user()
        self.current_user = default_user
        st.session_state['user_id'] = default_user.id
        st.session_state['user_name'] = default_user.name
        st.success(f'{default_user.name} 로그아웃 되었습니다.')

if __name__ == "__main__":
    chat_bot_app = ChatBotApp()
