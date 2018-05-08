from datetime import datetime, timedelta
import re
import time

def rj_parse_time(s_time):
    """
    'HH:MM:SS' or 'HH:MM' or 秒数 or 'now'を引数として受け取り、
    当日00:00:00からの差分としてtimedeltaオブジェクトとして返す
    """
    re_time = re.compile(r'^\d+:\d+:\d+|^\d+:\d+|\d+')
    re_now = re.compile(r'now', re.I)
    time = None

    if re.match(re_time, s_time):
        # 'HH:MM:SS' or 'HH:MM' or 秒数
        t = list(map(int, s_time.split(':')))
        if len(t) == 3:
            time = timedelta(seconds=(t[0] * 360) + (t[1] * 60) + t[2])
        elif len(t) == 2:
            time = timedelta(seconds=(t[0] * 360) + (t[1] * 60))
        elif len(t) == 1:
            time = timedelta(seconds=t[0])
    elif re.match(re_now, s_time):
        # 'now'
        n = datetime.now()
        n_sec = (n.hour * 360) + (n.minute * 60) + n.second
        time = timedelta(seconds=n_sec, microseconds=n.microsecond)

    return time

def rj_parse_date(s_date):
    """
    'YYYY/MM/DD|MM/DD|DD' or
    'sun|mon|tue|wed|thu|fri|sat' or
    'today' or
    '+Nd'
    を引数として受け取り、
    'YYYY/MM/DD 00:00:00'のdatetimeオブジェクトとして返す
    """
    re_wday = re.compile(r'^sun$|^mon$|^tue$|^wed$|^thu$|^fri$|^sat$', re.I)
    re_date = re.compile(r'^\d{4}/\d{1,2}/\d{1,2}$|^\d{1,2}/\d{1,2}$|^\d{1,2}$')
    re_today = re.compile(r'^today$', re.I)
    re_plus = re.compile(r'^\+(\d+)d$', re.I)
    date = None

    n = datetime.now()

    try:
        if re.match(re_wday, s_date):
            # Weekday
            wdaynum = {
                'mon': 0,
                'tue': 1,
                'wed': 2,
                'thu': 3,
                'fri': 4,
                'sat': 5,
                'sun': 6,
            }
            offset = wdaynum.get(s_date.lower()) - n.weekday()
            if offset < 0:
                # next week
                offset += 7
            date = datetime(n.year, n.month, n.day) + timedelta(days=offset)

        elif re.match(re_date, s_date):
            # YYYY/MM/DD or MM/DD or DD
            d = s_date.split('/')
            if len(d) == 3:
                year, month, day = map(int, d)
            elif len(d) == 2:
                month, day = map(int, d)
                year = n.year
            else:
                day = int(d[0])
                year = n.year
                month = n.month
            date = datetime(year, month, day)

        elif re.match(re_today, s_date):
            # today
            date = datetime(n.year, n.month, n.day)

        elif re.match(re_plus, s_date):
            # +n day
            offset = int(re.match(re_plus, s_date).group(1))
            date = datetime(n.year, n.month, n.day) + timedelta(days=offset)

    except ValueError:
        pass

    return date
