import streamlit as st
import openai
import time
import pandas as pd
from emailing import send_email, add_html_blocks, github_markup_to_html


def load_data():
    for table_name in ('pages', 'topic_prompts', 'prompts', 'text', 'clifton_strengths'):

        if table_name not in ss:
            df = pd.read_excel('data.xlsx', sheet_name=table_name, engine='openpyxl', index_col=0)
            ss[table_name] = df


def initiate_states():

    # Create default session states
    if 'messages' not in ss:
        ss['messages'] = [
            {"role": "system", "content": ss.prompts.at['system_message', 'prompt']},
        ]

    if 'state' not in ss:
        ss['state'] = "Intro"

    if 'model_reply' not in ss:
        ss['model_reply'] = ""

    if 'user_reply' not in ss:
        ss['user_reply'] = ""

    if 'current_topic' not in ss:
        ss['current_topic'] = ""

    if 'topics' not in ss:
        ss['topics'] = {}

    if 'counts' not in ss:
        ss['counts'] = 1

    if 'user_info' not in ss:
        ss['user_info'] = {}

    if 'load_questions' not in ss:
        ss['load_questions'] = False


def next_question():
    if ss.counts <= MAX_QUESTIONS:
        if len(ss.user_reply) > 2:
            local_prompt = ss.user_reply
            update_messages(local_prompt)
            ss.counts = ss.counts + 1
            ss.user_reply = ""
            st.session_state["reply"] = ""
        else:
            st.error(ss.text.at['error_too_short', 'text'])

    else:
        ss.state = 'Summary'
        local_prompt = ss.topic_prompts.at[ss.current_topic, 'summary_prompt']
        update_messages(local_prompt)


def display_headers():

    if not pd.isna(ss.pages.at[ss.state, 'title']):
        st.title(ss.pages.at[ss.state, 'title'])

    if not pd.isna(ss.pages.at[ss.state, 'subheader']):
        st.subheader(ss.pages.at[ss.state, 'subheader'])

    if not pd.isna(ss.pages.at[ss.state, 'markdown']):
        st.markdown(ss.pages.at[ss.state, 'markdown'])


def update_messages(local_prompt):
    ss.messages.append({"role": "assistant", "content": ss.model_reply})
    ss.messages.append({"role": "user", "content": local_prompt})
    ss.model_reply = ""
    ss.user_reply = ""


def update_model_response():
    """Calls the OpenAI API and updates model_response_display"""
    openai.api_key = st.secrets['SECRET_KEY']

    qu_attempts = 1
    while qu_attempts <= 10:

        try:
            response = []
            for resp in openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=ss.messages,
                    stream=True):
                if 'content' in resp['choices'][0]['delta']:
                    response.append(resp['choices'][0]['delta']['content'])
                    result = "".join(response).strip()
                    model_response_display.markdown(f'{result}')

            ss.model_reply = "".join(response).strip()
            qu_attempts = 11

        except:
            print(f"openai error, attempt {qu_attempts}")
            qu_attempts += 1
            time.sleep(2)

    st.experimental_rerun()


# Initiate states and variables
MAX_QUESTIONS = 3
ss = st.session_state
load_data()
initiate_states()

st.set_page_config(page_title=ss.text.at['page_title', 'text'], page_icon=ss.text.at['page_icon', 'text'],
                   layout="centered", initial_sidebar_state="collapsed", menu_items=None)


# Update display, dependent on state
match ss.state:

    case "Intro":
        st.image('cv_logo.png', width=150)

        display_headers()

        ss.user_info['strengths'] = st.multiselect(ss.text.at['strength_selection_text', 'text'],
                                                   ss.clifton_strengths.index.tolist(), max_selections=10)

        strengths = ", ".join(ss.user_info['strengths'])

        ss.current_topic = st.selectbox(ss.text.at['topic_selection_text', 'text'], ss.topic_prompts.index.tolist())

        if st.button("Next", type='primary'):
            ss.state = 'Questions'
            prompt_template = ss.topic_prompts.at[ss.current_topic, 'guidance_prompt']
            prompt = prompt_template.format(strengths=strengths)

            update_messages(prompt)

            ss.user_reply = ""
            st.experimental_rerun()

    case "Questions":

        display_headers()

        if ss.model_reply == "":
            model_response_display = st.empty()
            update_model_response()
        else:
            model_response_display = st.markdown(ss.model_reply)

        if ss.counts <= MAX_QUESTIONS:
            ss.user_reply = st.text_area("Response:", label_visibility='collapsed',
                                         placeholder=ss.text.at['user_reply_placeholder', 'text'],
                                         key='reply')

        st.button("Next", on_click=next_question, type='primary')

    case "Summary":

        st.image('cv_logo.png', width=150)
        display_headers()

        actions = []
        response = ['Error: No actions loaded...']

        if ss.model_reply == "":
            model_response_display = st.empty()
            update_model_response()
            st.experimental_rerun()
        else:
            response = ss.model_reply.split('::Suggestion::')
            model_response_display = st.markdown(response[0])

            for i, action in enumerate(response[1:]):
                action_text = action.strip()
                actions.append("")
                actions[i] = st.text_area(label=str(i), label_visibility='collapsed', value=action_text)

        col1, col2 = st.columns(2)

        with col1:
            email_address = st.text_input("Email address", label_visibility='collapsed', placeholder="Enter your email")
            if st.button("Send me a copy", type='primary'):

                action_bullets = ""
                for action in actions:
                    action_bullets = action_bullets + '* ' + action + '\n\n'

                html_blocks = {
                    '{summary}': github_markup_to_html(response[0]),
                    '{actions}': github_markup_to_html(action_bullets)
                }

                html_file_path = 'email_template.html'

                updated_html = add_html_blocks(html_file_path, html_blocks)

                if send_email(ss.text.at['email_subject', 'text'], updated_html, email_address):
                    st.text("Email sent!")
                else:
                    st.text(ss.text.at['email_error', 'text'])

        with col2:
            if st.button(ss.text.at['button_discuss_another_topic', 'text']):
                ss.state = 'Intro'
                ss['messages'] = [
                    {"role": "system", "content": ss.prompts.at['system_message', 'prompt']},
                ]
                ss.counts = 1
                st.experimental_rerun()
