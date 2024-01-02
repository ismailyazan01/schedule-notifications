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
def readSchedule(textfile):
    """
    Reads a schedule from a text file and stores it in the global schedule list.
    Each line in the file is expected to be either a header or an event.
    Events are expected to be in the format 'Event Description @ Time'.

    Parameters:
    textfile (str): The path to the text file containing the schedule.
    """
    with open(textfile, 'r') as file:
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
def readTime(eventTime):
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
        if "a" not in eventTime and "A" not in eventTime and "p" not in eventTime and "P" not in eventTime:
            if ":" not in eventTime:
                return eventTime + ":00:00"
            else:
                return eventTime + ":00"
        if "a" in eventTime or "A" in eventTime:
            if "12" not in eventTime[0:2] and ":" not in eventTime:
                return eventTime.split()[0] + ":00:00"
            elif "12" not in eventTime[0:2] and ":" in eventTime:
                return eventTime.split()[0] + ":00"
            elif "12" in eventTime[0:2] and ":" not in eventTime:
                return "00:00:00"
            elif "12" in eventTime[0:2] and ":" in eventTime:
                return "00:" + eventTime[3:5] + ":00"
        if "p" in eventTime or "P" in eventTime:
            if "12" not in eventTime[0:2] and ":" not in eventTime:
                return str(int(eventTime.split()[0]) + 12) + ":00:00"
            elif "12" not in eventTime[0:2] and ":" in eventTime:
                return str(int(eventTime.split(":")[0]) + 12) + ":" + eventTime.split(":")[1][:2] + ":00"
            elif "12" in eventTime[0:2] and ":" not in eventTime:
                return "12:00:00"
            elif "12" in eventTime[0:2] and ":" in eventTime:
                return eventTime.split()[0] + ":00"
    except ValueError:
        print("Invalid time format, please ensure the time is in the correct format.")
    except IndexError:
        print("Unexpected time format, unable to parse the time.")
    except TypeError:
        print("Invalid input type, expected a string.")


# Function to run the notification process
def runNotifications():
    """
    Runs the notification process by reading the schedule and sending emails
    at the specified times.
    """
    readSchedule("schedule.txt")  # Read the schedule from 'schedule.txt'

    for event in schedule[1:]:
        currentTime = datetime.now().strftime("%H:%M:%S")  # Get current time
        targetTime = event[1]  # Get the target time for the notification

        # Convert current_time and target_time to datetime objects
        currentDateTime = datetime.strptime(currentTime, "%H:%M:%S")
        targetDateTime = datetime.strptime(targetTime, "%H:%M:%S")

        # Calculate time difference
        timeDiff = (targetDateTime - currentDateTime).total_seconds()

        if timeDiff < 0:
            continue

        if "urgent" in event[0].lower():
            time.sleep(timeDiff - 300.0)
            emailAlert(schedule[0], str(event[0]) + " in 5 minutes!", os.getenv("TO_NUMBER"))
            emailAlert(event[1], str(event[0]) + " in 5 minutes!", os.getenv("TO_EMAIL"))
            timeDiff = 300

        # Wait until the target time and send an email alert
        print(f"Waiting for {timeDiff} seconds until {targetTime}")
        time.sleep(timeDiff)
        emailAlert(event[1], event[0], os.getenv("TO_EMAIL"))
        if "urgent" in event[0].lower():
            emailAlert(schedule[0], event[0], os.getenv("TO_NUMBER"))

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
        schedule.append(unaccountedEvent)


def endDayEventEntry():
    """
        Processes each event at the end of the day, asking the user if they completed it.
        Based on the user's response, it updates the event's status as complete or incomplete.
        """
    # Iterate through each event and update its completion status
    for event in schedule[1:]:
        if type(event) is list:
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
        "Prayers": ["fajir", "duhr", "asr", "maghrib", "isha", "jumuah"],
        "Reading": ["read", "reading"],
        "Workouts": ["workout", "exercise", "football", "basketball", "boeing", "soccer", "gym"],
        "Quran": ["quran", "halaqa"],
        "Coding": ["coding", "program"],
        "School": ["school", "class"]
    }

    for category, words in keywords.items():
        if any(word in eventLowerCase for word in words):
            identifier = category
            break

    if identifier == "":
        incompleteToDo.append(event)
        return

    # Execute the SQL query to update the event's status
    connection = connectToDatabase()
    cursor = connection.cursor()

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

    cursor.execute(update_query, (identifier,))
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


def dbDataRetrieval():
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
    columns = dbDataRetrieval()

    # Lists for the x-axis and the y-values of the bar graph
    xAxisEvents = []  # x-axis labels
    yAxisCompleted = []  # y-values for completed attempts
    yAxisIncomplete = []  # y-values for incomplete attempts

    # Populating the x, y1, and y2 lists with data
    for i in range(6):
        now = datetime.now()
        if columns[3][i]:
            difference = now - columns[3][i]

            # Calculate total seconds for time difference
            totalSeconds = difference.total_seconds()
            # Constants for seconds in a year and a day
            secondsInYear = 365.25 * 24 * 60 * 60
            secondsInDay = 24 * 60 * 60

            # Determine the appropriate time unit and calculate the difference
            if totalSeconds > secondsInYear:
                diff = totalSeconds // secondsInYear
                diffType = "year(s)"
            elif totalSeconds < secondsInDay:
                diff = totalSeconds // 3600
                diffType = "hour(s)"
            else:
                diff = difference.days
                diffType = "day(s)"

            # Append the formatted string and the corresponding values to the lists
            xAxisEvents.append(f"{str(columns[0][i])} \n in {diff}\n{diffType}")
            yAxisCompleted.append(columns[2][i])
            yAxisIncomplete.append(columns[1][i] - columns[2][i])
        else:
            xAxisEvents.append(columns[0][i])
            yAxisCompleted.append(columns[2][i])
            yAxisIncomplete.append(columns[1][i] - columns[2][i])

    # Calculate the combined values for each stack by adding the corresponding elements of
    # 'yAxisCompleted' and 'yAxisIncomplete', which represent the completed and incomplete portions
    stackedValues = yAxisCompleted + yAxisIncomplete

    # Find the maximum value among the combined stacked values to determine the highest point on the y-axis
    maxStackedValue = max(stackedValues)

    # Set the limits for the y-axis from 0 to 125% of the maximum stacked value to ensure there is
    # 25% extra space above the tallest bar in the stack
    plt.ylim(0, maxStackedValue * 1.25)

    # Creating a stacked bar graph with black edge coloring
    plt.bar(xAxisEvents, yAxisCompleted, color='c', edgecolor='k')
    plt.bar(xAxisEvents, yAxisIncomplete, bottom=yAxisCompleted, color='w', edgecolor='k')

    # Categories for the legend
    categories = ['Completed', 'Incomplete']

    # Adding a legend in the upper right corner
    plt.legend(categories, loc='upper right')

    plt.tight_layout()

    # Displaying the graph
    plt.show()


runNotifications()
