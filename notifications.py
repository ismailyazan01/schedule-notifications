import os
import smtplib
import time
from email.message import EmailMessage
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from a .env file
load_dotenv()

# Initialize an empty list to store the schedule
schedule = []


# Function to read the schedule from a text file
def read_schedule(txtfile):
    """
    Reads a schedule from a text file and stores it in the global schedule list.
    Each line in the file is expected to be either a header or an event.
    Events are expected to be in the format 'Event Description @ Time'.

    Parameters:
    txtfile (str): The path to the text file containing the schedule.
    """
    with open(txtfile, 'r') as file:
        for line in file:
            line = line.strip('\n')  # Remove newline characters
            if line[0] in '0123456789':
                # If the line starts with a digit, add it directly to the schedule
                schedule.append(line)
            else:
                # Otherwise, split the line at ' @ ' and process the time
                rendezvous = line.split(' @ ')
                rendezvous[1] = read_time(rendezvous[1])
                schedule.append([rendezvous[0], rendezvous[1]])


# Function to send an email alert
def email_alert(subject, body, to):
    """
    Sends an email alert.

    Parameters:
    subject (str): The subject of the email.
    body (str): The body content of the email.
    to (str): The recipient's email address.
    """
    msg = EmailMessage()
    msg.set_content(body)  # Set the email body
    msg['Subject'] = subject  # Set the email subject
    msg['to'] = to  # Set the recipient

    # Get the sender's email and password from environment variables
    user = os.getenv("EMAIL_USER")
    msg['From'] = user
    password = os.getenv("EMAIL_PASSWORD")

    # Connect to the SMTP server and send the email
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()  # Start TLS encryption
    server.login(user, password)  # Log in to the email account
    server.send_message(msg)  # Send the email

    server.quit()  # Close the connection to the server


# Function to process and format time strings
def read_time(time):
    """
    Converts time strings into a 24-hour format.

    Parameters:
    time_str (str): The time string to convert.

    Returns:
    str: The time string in 24-hour format.
    """
    try:
        # Process and convert time strings to 24-hour format
        # Additional logic here for handling 'am'/'pm' and other time formats
        if "a" not in time and "A" not in time and "p" not in time and "P" not in time:
            if ":" not in time:
                return time + ":00:00"
            else:
                return time + ":00"
        if "a" in time or "A" in time:
            if "12" not in time[0:2] and ":" not in time:
                return time.split()[0] + ":00:00"
            elif "12" not in time[0:2] and ":" in time:
                return time.split()[0] + ":00"
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


# Function to run the notification process
def run_notifications():
    """
    Runs the notification process by reading the schedule and sending emails
    at the specified times.
    """
    read_schedule("schedule.txt")  # Read the schedule from 'schedule.txt'

    for event in schedule[1:]:
        current_time = datetime.now().strftime("%H:%M:%S")  # Get current time
        target_time = event[1]  # Get the target time for the notification

        # Convert current_time and target_time to datetime objects
        current_datetime = datetime.strptime(current_time, "%H:%M:%S")
        target_datetime = datetime.strptime(target_time, "%H:%M:%S")

        # Calculate time difference
        time_diff = (target_datetime - current_datetime).total_seconds()

        # Wait until the target time and send an email alert
        print(f"Waiting for {time_diff} seconds until {target_time}")
        time.sleep(time_diff)
        email_alert(schedule[0], event[0], os.getenv("TO_NUMBER"))
        email_alert(schedule[0], event[0], os.getenv("TO_EMAIL"))


# Run the notification process
run_notifications()
