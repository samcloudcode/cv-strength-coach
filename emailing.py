import smtplib
import streamlit as st
from email.message import EmailMessage
import markdown

USER = st.secrets['GMAIL_SENDER']
PASS = st.secrets['GMAIL_PASS']


def send_email(subject, html_body, sendto):
    try:
        email_message = EmailMessage()
        email_message["Subject"] = subject
        email_message.set_content('This email does not support HTML content.')
        email_message.add_alternative(html_body, subtype='html')
        email_message['From'] = USER
        email_message['To'] = sendto

        gmail = smtplib.SMTP("smtp.gmail.com", 587)
        gmail.ehlo()
        gmail.starttls()
        gmail.login(USER, PASS)
        gmail.send_message(email_message)
        gmail.quit()

        return True

    except smtplib.SMTPRecipientsRefused:
        return False


def add_html_blocks(html_file_path, html_blocks):
    """
    Takes the path of an HTML file and a dictionary of HTML blocks, where the keys
    are placeholders in the file and the values are the HTML code to be inserted.
    Reads the contents of the HTML file, replaces the placeholders with the
    corresponding HTML blocks, and returns the updated HTML string.
    """
    with open(html_file_path, 'r') as f:
        html_template = f.read()

    for placeholder, html_block in html_blocks.items():
        html_template = html_template.replace(placeholder, html_block)

    return html_template


def github_markup_to_html(github_markup):
    """
    Converts GitHub-flavored Markdown to HTML and returns the resulting HTML string.
    """
    html = markdown.markdown(github_markup)
    return html
