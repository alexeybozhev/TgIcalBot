import requests
import json

from ics import Calendar
from datetime import datetime, timedelta
from dateutil.rrule import rrulestr
from pathlib import Path

# Constants
CURRENT_DIRECTORY = Path(__file__).parent
ICAL_FILE = CURRENT_DIRECTORY / 'events.ics'

PROCESSED_EVENTS_FILE = CURRENT_DIRECTORY / "processed_events.txt"

with open('config.json') as f:
    config = json.load(f)

def load_config_from_file(file_path):
    with open(file_path, 'r') as f:
        config = json.load(f)  # Чтение JSON из файла

    webhook_url = config.get("WEBHOOK_URL")
    chat_id = config.get("CHAT_ID")

    return webhook_url, chat_id

WEBHOOK_URL, CHAT_ID = load_config_from_file('config.json')
print(f"WEBHOOK_URL: {WEBHOOK_URL}, CHAT_ID: {CHAT_ID}")

def load_processed_events(file_path):
    """Load the set of processed event IDs from a file."""
    try:
        with open(file_path, "r") as f:
            return set(f.read().splitlines())
    except FileNotFoundError:
        return set()


def save_processed_event(file_path, event_id):
    """Append a processed event ID to the file."""
    with open(file_path, "a") as f:
        f.write(event_id + "\n")


def parse_rrule(event):
    """Parse RRULE and EXRULE from event and return a dictionary."""
    result_dict = {}
    for item in event.extra:
        result_dict[item.name] = item.value

    return result_dict, event.begin


def generate_event_occurrences(rrule_value, dtstart, from_date, to_date):
    """Generate occurrences of a recurring event using RRULE."""
    return list(rrulestr(rrule_value, dtstart=dtstart).between(from_date, to_date, inc=True))


def handle_exrule(exrule_value, events, dtstart, start_date, end_date):
    """Handle EXRULE to exclude specific occurrences."""
    if exrule_value:
        for occurrence in rrulestr(exrule_value, dtstart=dtstart).between(start_date, end_date, inc=True):
            print(f"Occurrence excluded: {occurrence}")
            if occurrence in events:
                events.remove(occurrence)
    return events


def expand_event(event, start_date, end_date):
    """Generate occurrences of a recurring event within a date range."""
    result_dict, dtstart = parse_rrule(event)
    if not result_dict:
        print(f"No RRULE found for event '{event.name}'. Skipping.")
        return []
    occurrences = generate_event_occurrences(result_dict["RRULE"], dtstart, start_date, end_date)

    exrule_value = result_dict.get("EXRULE")
    occurrences = handle_exrule(exrule_value, occurrences, dtstart, start_date, end_date)

    result = list()
    for occurrence in occurrences:
        result.append(datetime.combine(occurrence.date(), dtstart.time()))

    print(f"Event {event.name} occurrences between {start_date} and {end_date}: {len(occurrences)}")
    return result


def send_notification(event_name, chat_id):
    """Send a notification for the event."""
    payload = {"chat_id": chat_id, "text": event_name}
    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        return response.status_code
    except requests.RequestException as e:
        print(f"Error sending notification: {e}")
        return None


def process_events():
    """Process and send notifications for events."""
    calendar = open_calendar(ICAL_FILE)

    processed_events = load_processed_events(PROCESSED_EVENTS_FILE)
    now = datetime.now()
    start_date = now - timedelta(days=1)
    end_date = now + timedelta(days=1)

    for event in calendar.events:
        occurrences = expand_event(event, start_date, end_date)
        for event_start in occurrences:
            event_end = event_start + event.duration
            event_start_str = event_start.strftime("%Y-%m-%d")
            event_id = f"{event.name}_{event_start_str}"

            if event_start <= now <= event_end and event_id not in processed_events:
                status_code = send_notification(event.name + f":\n{event.location}", CHAT_ID)
                if status_code == 200:
                    print(f"Success sending notification for event '{event.name}'")
                    save_processed_event(PROCESSED_EVENTS_FILE, event_id)
                else:
                    print(f"Error sending notification for event '{event.name}': {status_code}")


def open_calendar(filename):
    with open(filename, "r") as file:
        calendar = Calendar(file.read())
    return calendar

if __name__ == "__main__":
    process_events()
