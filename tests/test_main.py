import unittest
from datetime import datetime
from unittest.mock import patch, mock_open

import main
from main import (
    load_processed_events, save_processed_event, parse_rrule,
    generate_event_occurrences, handle_exrule, expand_event, send_notification
)


class TestEventProcessor(unittest.TestCase):

    def setUp(self):
        self.sample_calender = main.open_calendar("test.ics")
        self.sample_event = list(self.sample_calender.events)[0]
        self.from_date = datetime(2025, 1, 9)
        self.to_date = datetime(2025, 1, 31)

    @patch("builtins.open", new_callable=mock_open, read_data="event1\nevent2")
    def test_load_processed_events(self, mock_file):
        processed_events = load_processed_events("processed_events.txt")
        self.assertEqual({"event1", "event2"}, processed_events)

    @patch("builtins.open", new_callable=mock_open)
    def test_save_processed_event(self, mock_file):
        save_processed_event("processed_events.txt", "event3")
        mock_file().write.assert_called_once_with("event3\n")

    def test_parse_rrule(self):
        result_dict, dtstart = parse_rrule(self.sample_event)
        self.assertIn("RRULE", result_dict)
        self.assertIn("EXRULE", result_dict)

        self.assertEqual("FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=11", result_dict["RRULE"])
        self.assertEqual("FREQ=WEEKLY;INTERVAL=2;BYDAY=MO;BYHOUR=11", result_dict["EXRULE"])

        self.assertEqual(datetime(2024, 12, 30, 11, 0), dtstart.datetime.replace(tzinfo=None))

    def test_generate_event_occurrences(self):
        dtstart = datetime(2024, 1, 8, 10, 0)
        occurrences = generate_event_occurrences("FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR", dtstart, self.from_date, self.to_date)
        self.assertEqual(16, len(occurrences))

    def test_handle_exrule(self):
        dtstart = datetime(2024, 12, 30, 11, 0)
        events = generate_event_occurrences("FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR", dtstart, self.from_date, self.to_date)
        filtered_events = handle_exrule("FREQ=WEEKLY;INTERVAL=2;BYDAY=MO", events, dtstart, self.from_date, self.to_date)
        self.assertEqual(14, len(filtered_events))
        self.assertNotIn(datetime(2025, 1, 13, 11, 0), filtered_events)
        self.assertNotIn(datetime(2025, 1, 27, 11, 0), filtered_events)

    def test_expand_event(self):
        # Генерируем события
        occurrences = expand_event(self.sample_event, self.from_date, self.to_date)

        # Ожидаемые даты
        expected_occurrences = [
            datetime(2025, 1, 9, 11, 0),
            datetime(2025, 1, 10, 11, 0),
            # datetime(2025, 1, 13, 11, 0), - планирование
            datetime(2025, 1, 14, 11, 0),
            datetime(2025, 1, 15, 11, 0),
            datetime(2025, 1, 16, 11, 0),
            datetime(2025, 1, 17, 11, 0),
            datetime(2025, 1, 20, 11, 0),
            datetime(2025, 1, 21, 11, 0),
            datetime(2025, 1, 22, 11, 0),
            datetime(2025, 1, 23, 11, 0),
            datetime(2025, 1, 24, 11, 0),
            # datetime(2025, 1, 27, 11, 0), - планирование
            datetime(2025, 1, 28, 11, 0),
            datetime(2025, 1, 29, 11, 0),
            datetime(2025, 1, 30, 11, 0),
        ]

        self.assertEqual(len(expected_occurrences), len(occurrences))
        self.assertEqual(expected_occurrences, occurrences)

    @patch("requests.post")
    def test_send_notification(self, mock_post):
        mock_post.return_value.status_code = 200
        status_code = send_notification("Test Event", 777)
        self.assertEqual(200, status_code)
        mock_post.assert_called_once_with(
            "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage",
            data={"chat_id": 777, "text": "Test Event"}
        )

if __name__ == "__main__":
    unittest.main()
