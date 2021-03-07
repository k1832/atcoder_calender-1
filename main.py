#from __future__ import print_function
import sys, os
import datetime
import requests, bs4
import json
import urllib.parse as urlparse
from datetime import datetime as dt
from typing import Final, List, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

from modules.calendar_event import CalendarEvent

SCOPES: Final[List[str]] = ['https://www.googleapis.com/auth/calendar']
CREDENTIAL_JSON = json.load(os.environ.get('CREDENTIAL_JSON'))
API_CREDENTIAL: Final[Any] = service_account.Credentials.from_service_account_file(CREDENTIAL_JSON, scopes=SCOPES)
API_SERVICE: Final[Any] = build('calendar', 'v3', credentials=API_CREDENTIAL)
CALENDAR_ID: Final[Any] = 's1c5d19mg7bo08h10ucio8uni8@group.calendar.google.com'
ATCODER_BASE_URL: Final[str] = 'https://atcoder.jp/'

def parse_event(name_obj, start_datetime_obj, duration_obj) -> CalendarEvent:
    contest_title = name_obj.text
    contest_url = urlparse.urljoin(ATCODER_BASE_URL, name_obj.attrs['href'])
    start_at = dt.strptime(start_datetime_obj.text, '%Y-%m-%d %H:%M:%S+0900')
    contest_hours, contest_minutes = map(int, duration_obj.text.split(':'))
    contest_duration = datetime.timedelta(hours=contest_hours, minutes=contest_minutes)
    end_at = start_at + contest_duration
    return CalendarEvent(
        summary=contest_title, start_at=start_at, end_at=end_at, description=contest_url
    )

def get_atcoder_schedule() -> List[CalendarEvent]:
    res = requests.get(urlparse.urljoin(ATCODER_BASE_URL, "contests"))
    res.raise_for_status()
    soup = bs4.BeautifulSoup(res.content, 'html.parser')

    contest_table = soup.find('div', id='contest-table-upcoming').find('table')
    start_datetime_objs = contest_table.select('tbody tr > td:nth-child(1)')
    name_objs = contest_table.select('tbody tr > td:nth-child(2) > a')
    duration_objs = contest_table.select('tbody tr > td:nth-child(3)')

    # コンテストの名前・開始時間・制限時間の数は同じ必要がある
    if not (len(name_objs) == len(start_datetime_objs) == len(duration_objs)):
        print("Failed to retrieve all the contests info.")
        sys.exit(1)

    event_list = [
        parse_event(name_obj, start_datetime_obj, duration_obj)
        for name_obj, start_datetime_obj, duration_obj in zip(name_objs, start_datetime_objs, duration_objs)
    ]

    return event_list

# google calender api を使う部分．サンプルそのまま
def add_event(event: CalendarEvent, created_at: datetime.datetime):
    if event.description:
        event.description += '\n'
    event.description += f'UPDATED AT: {created_at.isoformat()}'
    added_event = API_SERVICE.events().insert(calendarId=CALENDAR_ID, body=event.get_as_obj()).execute()
    print (added_event['id'])

def delete_contests(time_from, time_to):
    API_SERVICE.events().list(
        calendarId=CALENDAR_ID,
        timeMin=f"{time_from.isoformat()}Z",
        timeMax=f"{time_to.isoformat()}Z",
    ).delete().execute()

def main():
    event_list = get_atcoder_schedule()
    print(event_list)
    now = datetime.datetime.utcnow()
    eight_week_later = now + datetime.timedelta(weeks=8)
    delete_contests(time_from=now, time_to=eight_week_later)

    # 取得した各コンテストについてループ
    if not event_list:
        print("There is no upcoming contests.")
        sys.exit()

    for event in event_list:
        if event.start.time > eight_week_later:
            continue
        add_event(event, now)

if __name__ == '__main__':
    main()
