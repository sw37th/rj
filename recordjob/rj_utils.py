import re
import datetime
import time

def analyze_time(str_time):
    """
    'HH:MM:SS' or 'HH:MM' or 秒数 or 'now'を引数として受け取り、
    当日00:00:00からの差分としてtimedeltaオブジェクトとして返す
    """
    re_time = re.compile(r'^\d+:\d+:\d+|^\d+:\d+|\d+')
    re_now = re.compile(r'now', re.I)
    time = None

    if re.match(re_time, str_time):
        # 'HH:MM:SS' or 'HH:MM' or 秒数
        t = list(map(int, str_time.split(':')))
        if len(t) == 3:
            time = datetime.timedelta(seconds=(t[0]*60*60)+(t[1]*60)+t[2])
        elif len(t) == 2:
            time = datetime.timedelta(seconds=(t[0]*60*60)+(t[1]*60))
        elif len(t) == 1:
            time = datetime.timedelta(seconds=t[0])
    elif re.match(re_now, str_time):
        # 'now'
        current = datetime.datetime.now()
        time = (datetime.timedelta(
                seconds=(current.hour*60*60)+(current.minute*60)+current.second,
                microseconds=current.microsecond))

    return time

def analyze_date(str_date):
    """
    'YYYY/MM/DD' or 'MM/DD' or 'DD' or 'sun|mon|tue|wed|thu|fri|sat'を引数として受け取り、
    'YYYY/MM/DD 00:00:00'のdatetimeオブジェクトとして返す
    """
    # "YYYY/MM/DD" or "MM/DD" or "DD" or "sun|mon|tue|wed|thu|fri|sat"
    re_wday = re.compile(r'^sun$|^mon$|^tue$|^wed$|^thu$|^fri$|^sat$', re.I)
    re_date = re.compile(r'^\d{4}/\d{1,2}/\d{1,2}$|^\d{1,2}/\d{1,2}$|^\d{1,2}$')
    re_today = re.compile(r'^today$', re.I)
    re_plus = re.compile(r'^\+(\d+)d$', re.I)

    current = datetime.datetime.now()

    date = None

    if re.match(re_wday, str_date):
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
        today = current.weekday()
        offset = wdaynum[str_date.lower()] - today
        if offset < 0:
            offset += 7
        date = (datetime.datetime(current.year, current.month, current.day) +
                datetime.timedelta(days=offset))

    elif re.match(re_date, str_date):
        # YYYY/MM/DD or MM/DD or DD
        d = str_date.split('/')
        if len(d) == 3:
            year, month, day = map(int, d)
        elif len(d) == 2:
            month, day = map(int, d)
            year = current.year
        else:
            day = int(d[0])
            year = current.year
            month = current.month
        date = datetime.datetime(year, month, day)
    elif re.match(re_today, str_date):
        # today
        date = datetime.datetime(current.year, current.month, current.day)
    elif re.match(re_plus, str_date):
        # +n day
        n = re.match(re_plus, str_date).group(1)
        date = (datetime.datetime(current.year, current.month, current.day) +
                datetime.timedelta(days=int(n)))

    return date
