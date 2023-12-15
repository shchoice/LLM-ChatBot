import time
from typing import List

import numpy as np
import requests
from openai import OpenAI
import streamlit as st

BASE_URL ='http://localhost:8000'
CHATGPT_3_API_URL = BASE_URL + '/chat/gpt3'
CHATGPT_4_API_URL = BASE_URL + '/chat/gpt4'

SYSTEM_MSG = "You are a helpful assistant"

class ChatBotApp:
    def __init__(self):
        self.client = OpenAI()
        self.model_name = None
        self.temperature = 0.2
        self.max_tokens = 256
        self.counter_placeholder = None
        self.initialize_session_state()
        self.setup_ui()

    def initialize_session_state(self):
        # Initialise session state variables
        if 'generated' not in st.session_state:
            st.session_state['generated'] = []
        if 'past' not in st.session_state:
            st.session_state['past'] = []
        if 'messages' not in st.session_state:
            st.session_state['messages'] = []
        if 'model_name' not in st.session_state:
            st.session_state['model_name'] = []
        if 'cost' not in st.session_state:
            st.session_state['cost'] = []
        if 'total_tokens' not in st.session_state:
            st.session_state['total_tokens'] = []
        if 'total_cost' not in st.session_state:
            st.session_state['total_cost'] = 0.0

    def setup_ui(self):
        # Setting page title and header
        st.set_page_config(page_title="Seohwan Choi's ChatGPT", page_icon=":robot_face:")
        st.markdown("<h1 style='text-align: center;'>Seohwan Choi's ChatGPT🤩</h1>", unsafe_allow_html=True)
        self.sidebar_setup()
        self.main_chat_window()

    def sidebar_setup(self):
        st.sidebar.title('Chat Settings')

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

        st.sidebar.markdown('<h4>Usage</h4>', unsafe_allow_html=True)
        self.counter_placeholder = st.sidebar.empty()
        self.update_total_cost()

        clear_button = st.sidebar.button("Clear Conversation", key="clear")
        if clear_button:
            self.reset_session_state()

    def reset_session_state(self):
        st.session_state['generated'] = []
        st.session_state['past'] = []
        st.session_state['messages'] = []
        st.session_state['model_name'] = []
        st.session_state['total_tokens'] = []
        st.session_state['cost'] = []
        st.session_state['total_cost'] = 0.0

        self.update_total_cost()

    def update_total_cost(self):
        self.counter_placeholder.write(f"Total costs: ${st.session_state['total_cost']:.5f}")

    def main_chat_window(self):
        self.initialize_session_state()
        if st.session_state['generated']:
            self.display_chat_history()
        if user_input := st.chat_input(""):
            if user_input:
                self.handle_user_input(user_input)

            with st.chat_message('user'):
                user_input = st.session_state["past"][-1]
                st.markdown(user_input)

            with st.chat_message('assistant'):
                message_placeholder = st.empty()
                full_response = ""
                for lines in st.session_state['generated'][-1].split('\n'):
                    for chunk in lines.split():
                        full_response += chunk + " "
                        time.sleep(0.05)
                        message_placeholder.markdown(full_response)
                st.write(
                    f"Model used: {st.session_state['model_name'][-1]} \t"
                    f"Number of tokens: {st.session_state['total_tokens'][-1]} \t"
                    f"Cost: ${st.session_state['cost'][-1]:.5f}"
                )

    def handle_user_input(self, user_input):
        chatbot_message, total_tokens, prompt_tokens, completion_tokens = self.generate_response(user_input)
        st.session_state['past'].append(user_input)
        st.session_state['generated'].append(chatbot_message)
        st.session_state['total_tokens'].append(total_tokens)
        st.session_state['model_name'].append(self.model_name)

        cost = (total_tokens * 0.002 / 1000) if self.model_name == "gpt-3.5-turbo"\
            else (prompt_tokens * 0.03 + completion_tokens * 0.06) / 1000
        st.session_state['cost'].append(cost)
        st.session_state['total_cost'] += cost
        self.update_total_cost()

        # # For Debug
        # print(st.session_state['generated'])
        # print(st.session_state['past'])
        # print(st.session_state['messages'])
        # print(st.session_state['model_name'])
        # print(st.session_state['total_tokens'])
        # print(st.session_state['cost'])
        # print(st.session_state['total_cost'])
        # print()

    def generate_response(self, prompt):
        st.session_state['messages'].append({"role": "user", "content": prompt})

        completion = self.request_chat_api(
            model=self.model_name,
            message=st.session_state['messages'], # 대화했던 모든 메세지가 함께 날아감
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

        chatbot_message = completion.get('message', None)
        total_tokens = completion.get('total_tokens', 0)
        prompt_tokens = completion.get('prompt_tokens', 0)
        completion_tokens = completion.get('completion_tokens', 0)

        st.session_state['messages'].append({"role": "assistant", "content": chatbot_message})

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
        elif model_name == 'gpt-4':
            return CHATGPT_4_API_URL

    def display_chat_history(self):
        for i, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

                if (i+1) % 2 == 0:
                    st.write(
                        f"Model used: {st.session_state['model_name'][int(i/2)]}     "
                        f"Number of tokens: {st.session_state['total_tokens'][int(i/2)]}     "
                        f"Cost: ${st.session_state['cost'][int(i/2)]:.5f}"
                    )


if __name__ == "__main__":
    chat_bot_app = ChatBotApp()
