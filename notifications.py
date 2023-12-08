import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()


def email_alert(subject, body, to):
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['to'] = to

    user = os.getenv("EMAIL_USER")
    msg['From'] = user
    password = os.getenv("EMAIL_PASSWORD")

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(user, password)
    server.send_message(msg)

    server.quit()


email_alert("Schedule", "Coding Curriculum @ 9:30 AM", os.getenv("TO_EMAIL"))

