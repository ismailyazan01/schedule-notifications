import os
import smtplib
import time
from email.message import EmailMessage
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

schedule = []


def read_schedule(txtfile):
    with open(txtfile, 'r') as file:
        for line in file:
            line = line.strip('\n')
            if line[0] in '0123456789':
                schedule.append(line)
            else:
                rendezvous = line.split(' @ ')
                rendezvous[1] = read_time(rendezvous[1])
                schedule.append([rendezvous[0], rendezvous[1]])


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


def read_time(time):
    try:
        if "a" not in time and "A" not in time and "p" not in time and "P" not in time:
            if ":" not in time:
                return time + ":00"
            else:
                return time
        if "a" in time or "A" in time:
            if "12" not in time[0:2] and ":" not in time:
                return time.split()[0] + ":00:00"
            elif "12" not in time[0:2] and ":" in time:
                return time.split()[0]+ ":00"
            elif "12" in time[0:2] and ":" not in time:
                return "00:00:00"
            elif "12" in time[0:2] and ":" in time:
                return "00:" + time[3:5] + ":00"
        if "p" in time or "P" in time:
            if "12" not in time[0:2] and ":" not in time:
                return str(int(time.split()[0]) + 12) + ":00:00"
            elif "12" not in time[0:2] and ":" in time:
                return str(int(time.split(":")[0]) + 12) + ":" + time.split(":")[1][:2] + ":00"
            elif "12" in time[0:2] and ":" not in time:
                return "12:00:00"
            elif "12" in time[0:2] and ":" in time:
                return time.split()[0] + ":00"
    except Exception as e:
        print("Invalid input")

def run_notifications():
    read_schedule("schedule.txt")
    for event in schedule[1:]:
        current_time = datetime.now().strftime("%H:%M:%S")
        target_time = event[1]

        # Convert current_time and target_time to datetime objects
        current_datetime = datetime.strptime(current_time, "%H:%M:%S")
        target_datetime = datetime.strptime(target_time, "%H:%M:%S")

        # Calculate time difference
        time_diff = (target_datetime - current_datetime).total_seconds()
        if time_diff > 0:
            print(f"Waiting for {time_diff} seconds until {target_time}")
            time.sleep(time_diff)
            email_alert(schedule[0], event[0], os.getenv("TO_EMAIL"))


run_notifications()
