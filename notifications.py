import os
import smtplib
import time
from email.message import EmailMessage
from dotenv import load_dotenv
from datetime import datetime
import mysql.connector
import matplotlib.pyplot as plt


# Load environment variables from a .env file
load_dotenv()

# Initialize an empty list to store the schedule
schedule = []
incompleteToDo = []


# Function to read the schedule from a text file
def readSchedule(txtfile):
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
                rendezvous[1] = readTime(rendezvous[1])
                schedule.append([rendezvous[0], rendezvous[1]])


# Function to send an email alert
def emailAlert(subject, body, to):
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
def readTime(time):
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
def runNotifications():
    """
    Runs the notification process by reading the schedule and sending emails
    at the specified times.
    """
    readSchedule("schedule.txt")  # Read the schedule from 'schedule.txt'

    for event in schedule[1:]:
        current_time = datetime.now().strftime("%H:%M:%S")  # Get current time
        target_time = event[1]  # Get the target time for the notification

        # Convert current_time and target_time to datetime objects
        current_datetime = datetime.strptime(current_time, "%H:%M:%S")
        target_datetime = datetime.strptime(target_time, "%H:%M:%S")

        # Calculate time difference
        time_diff = (target_datetime - current_datetime).total_seconds()

        if time_diff < 0:
            continue

        if "urgent" in event[0].lower():
            time.sleep(time_diff - 300.0)
            emailAlert(event[1], event[0], os.getenv("TO_EMAIL"))
            time_diff = 300

        # Wait until the target time and send an email alert
        print(f"Waiting for {time_diff // 60} minutes until {target_time} for {event[0]}")
        time.sleep(time_diff)
        emailAlert(event[1], event[0], os.getenv("TO_EMAIL"))

        if "urgent" in event[0].lower():
            time.sleep(300.0)
            emailAlert(event[1], event[0], os.getenv("TO_EMAIL"))
    # Handle unaccounted events and database connection at the end of the day
    unaccountedEventsMethod()
    connectToDatabase()
    endDayEventEntry()


def unaccountedEventsMethod():
    """
        Interactively adds unaccounted events to the schedule. It prompts the user to enter
        events and specify if they are recurring. The process continues until the user types 'done'.
        """
    # Prompt user for unaccounted events until they signal completion
    unaccountedEvent = ""
    while unaccountedEvent.lower() != "done":
        unaccountedEvent = input("Add unaccounted for events(Type \"done\" to quit): ")
        if unaccountedEvent.lower() == "done":
            return
        recurring = input("Add recurring(Y or N)? ")
        if recurring.lower() == 'y':
            schedule.append("(Recurring) " + unaccountedEvent)
        else:
            schedule.append(unaccountedEvent)


def endDayEventEntry():
    """
        Processes each event at the end of the day, asking the user if they completed it.
        Based on the user's response, it updates the event's status as complete or incomplete.
        """
    # Iterate through each event and update its completion status
    for event in schedule[1:]:
        if type(event) == list:
            curEvent = event[0]
        else:
            curEvent = event
        if input(f"Did you complete this event: \"{curEvent}\"(Y or N)? ").lower() == 'n':
            recurringEvents(curEvent, False)
        else:
            recurringEvents(curEvent, True)


def recurringEvents(event, complete):
    """
    Updates the event's completion and planned status in the database.
    It determines the event's category and constructs the appropriate SQL query to update the database.

    Parameters:
    event (str): The name of the event to update.
    complete (str): 'Y' if the event was completed, 'N' otherwise.
    """
    # Determine the event's category and construct the SQL query
    identifier = ""
    eventLowerCase = event.lower()

    keywords = {
        "Prayer": ["fajir", "duhr", "asr", "maghrib", "isha", "jumuah"],
        "Reading": ["read", "reading"],
        "Workout": ["workout", "exercise", "football", "basketball", "boeing", "soccer", "gym"],
        "Quran": ["quran", "halaqa"],
        "Coding": ["coding", "program"],
        "School": ["school", "class"]
    }

    for category, words in keywords.items():
        if any(word in eventLowerCase for word in words):
            identifier = category
            break

    # Execute the SQL query to update the event's status
    connection = connectToDatabase()
    cursor = connection.cursor()

    if "(recurring)" not in eventLowerCase:
        incompleteToDo.append(event)
        return

    showValueQuery = "SELECT planned FROM events WHERE event_name = %s"
    cursor.execute(showValueQuery, (identifier,))
    result = cursor.fetchone()[0]

    if result == 0:
        firstPlannedQuery = "UPDATE events SET first_planned = CURRENT_TIMESTAMP WHERE event_name = %s"
        cursor.execute(firstPlannedQuery, (identifier,))

    if complete:
        update_query = "UPDATE events SET completed = completed + 1, planned = planned + 1 WHERE event_name = %s"
    else:
        update_query = "UPDATE events SET planned = planned + 1 WHERE event_name = %s"

    cursor.execute(update_query, (identifier, ))
    connection.commit()

    cursor.close()
    connection.close()


def connectToDatabase():
    """
        Establishes a connection to the database using credentials from environment variables.

        Returns:
        Connection object: The connection to the database.
        """
    # Connect to the MySQL database with credentials from environment variables
    db_connection = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    return db_connection


def clearDatabase():
    """
    This function clears all entries in the 'events' table of the database by setting
    the 'planned' and 'completed' columns to 0, and 'first_planned' to NULL.
    """
    # Establishing a database connection
    connection = connectToDatabase()
    cursor = connection.cursor()

    # SQL query to reset the event data
    clearDatabaseQuery = "UPDATE events SET planned = 0, completed = 0, first_planned = NULL;"

    # Executing the SQL query
    cursor.execute(clearDatabaseQuery)
    # Committing the changes to the database
    connection.commit()

    # Closing the cursor and the database connection
    cursor.close()
    connection.close()


def db_dataRetreival():
    """
    Retrieves data from the 'events' table in the database and organizes it into columns.

    Returns:
        A list of lists, where each sublist contains a column from the 'events' table.
    """
    # Establishing a database connection
    connection = connectToDatabase()
    cursor = connection.cursor()

    # Initializing a list of lists for each column
    columns = [[], [], [], []]

    # SQL query to retrieve data from all columns in 'events'
    query = "SELECT event_name, planned, completed, first_planned FROM events"
    # Executing the query
    cursor.execute(query)
    # Fetching all results from the executed query
    result = cursor.fetchall()

    # Unpacking the results into separate lists for each column
    for event_name, planned, completed, first_planned in result:
        columns[0].append(event_name)
        columns[1].append(planned)
        columns[2].append(completed)
        columns[3].append(first_planned)

    # Closing the cursor and the database connection
    cursor.close()
    connection.close()

    # Returning the organized data
    return columns


def graphEvents():
    """
    Retrieves event data from the database and creates a stacked bar graph.
    The graph displays the number of completed and incomplete attempts for each event.
    """
    # Retrieve event data from the database
    columns = db_dataRetreival()

    # Lists for the x-axis and the y-values of the bar graph
    x = []  # x-axis labels
    y1 = [] # y-values for completed attempts
    y2 = [] # y-values for incomplete attempts

    # Populating the x, y1, and y2 lists with data
    for i in range(6):
        now = datetime.now()
        difference = now - columns[3][i]

        # Calculate total seconds for time difference
        totalSeconds = difference.total_seconds()
        # Constants for seconds in a year and a day
        secondsInYear = 365.25 * 24 * 60 * 60
        secondsInDay = 24 * 60 * 60

        # Determine the appropriate time unit and calculate the difference
        if difference > secondsInYear:
            diff = totalSeconds // secondsInYear
            diffType = "year(s)"
        elif difference < secondsInDay:
            diff = totalSeconds // 3600
            diffType = "hour(s)"
        else:
            diff = difference.days
            diffType = "day(s)"

        # Append the formatted string and the corresponding values to the lists
        x.append(f"{str(columns[0][i])} \n in {diff} {diffType}")
        y1.append(columns[2][i])
        y2.append(columns[1][i] - columns[2][i])

    # Creating a stacked bar graph with black edge coloring
    plt.bar(x, y1, color='c', edgecolor='k')
    plt.bar(x, y2, bottom=y1, color='w', edgecolor='k')

    # Categories for the legend
    categories = ['Completed', 'Incomplete']

    # Adding a legend in the upper right corner
    plt.legend(categories, loc='upper right')

    # Displaying the graph
    plt.show()


# Run the notification process
runNotifications()
graphEvents()
clearDatabase()