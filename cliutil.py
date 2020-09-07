from datetime import datetime, timedelta
import re
import sys

def is_future(begin):
    """
    begin: 録画開始時刻 (datetime)

    beginが現在時刻より未来の場合にTrueを返す
    """
    now = datetime.now()
    if begin > now:
        return True
    else:
        return False

def parse_start_time(datestr, timestr, wormup_sec=0, day_change_hour=0):
    """
    datestr: (str)
        'YYYY/MM/DD|MM/DD|DD' or
        'sun|mon|tue|wed|thu|fri|sat' or
        'today' or
        '+Nd'
    timestr: (str)
        'HH:MM:SS' or 'HH:MM' or 'seconds'
    wormup_sec: (int)
        録画開始までのマージン
        ジョブがスタートしてから実際に録画開始されるまでのタイムラグを考慮し
        指定時刻よりwormup_sec秒だけジョブ開始時刻を早める。
    day_change_hour: (int)

    """
    begin = None
    re_date = re.compile(r'^\d{4}/\d{1,2}/\d{1,2}$|^\d{1,2}/\d{1,2}$')
    re_wday = re.compile(r'^sun$|^mon$|^tue$|^wed$|^thu$|^fri$|^sat$', re.I)
    re_today = re.compile(r'^today$', re.I)
    re_increase = re.compile(r'^\+(\d+)$')

    if re_date.match(datestr):
        date_ = parse_yyyymmdd(datestr)
    elif re_wday.match(datestr):
        date_ = parse_weekday(datestr, day_change_hour)
    elif re_today.match(datestr):
        date_ = parse_today(day_change_hour)
    elif re_increase.match(datestr):
        increase = int(re_increase.match(datestr).group(1))
        date_ = parse_increase(increase)
    else:
        date_ = None

    if date_:
        time_ = parse_time(timestr)
    if time_:
        begin = date_ + time_ - wormup_sec

    return begin

def parse_yyyymmdd(datestr):
    """
    datestr: (str)
        '[YYYY/]MM/DD or
        'sun|mon|tue|wed|thu|fri|sat' or
        'today' or
        '+n'

    datetimeオブジェクトに変換して返す
    """
    date_ = None
    now = datetime.now()

    try:
        d = [int(i) for i in datestr.split('/')]
        if len(d) == 3:
            year, month, day = d
        elif len(d) == 2:
            month, day = d
            if month == 1 and now.month == 12:
                # 年またぎ予約対応
                year = now.year + 1
            else:
                year = now.year
        date_ = datetime(year, month, day)
    except ValueError:
        pass

    return date_

def parse_weekday(datestr, day_change_hour):
    """
    datestr: (str)
        'sun|mon|tue|wed|thu|fri|sat' or
    day_change_hour: (int)

    実行時の日付けを基準に、指定曜日までの日数を加算した
    datetimeオブジェクトを返す

    午前0時以降day_change_hour時未満に前曜日が指定された場合は
    まだ日付が変わっていないと見なす
    """
    now = datetime.now()
    wdaynum = {
        'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3,
        'fri': 4, 'sat': 5, 'sun': 6}
    offset = wdaynum.get(datestr.lower()) - now.weekday()
    if offset < 0:
        # next week
        offset += 7
    if offset == 6 and now.hour < day_change_hour):
        # 午前0時以降day_change_hour時未満に前曜日が指定された
        offset = -1

    return datetime(now.year, now.month, now.day) + timedelta(days=offset)

def parse_today(day_change_hour):
    """
    day_change_hour: (int)

    本日の日付けのdatetimeオブジェクトを返す
    実行時刻がday_change_hour時刻未満の場合はまだ前日扱い
    """
    now = datetime.now()
    if now.hour < day_change_hour:
        # 前日の日付け扱い
        date_ = datetime(now.year, now.month, now.day) - timedelta(days=1)
    else:
        date_ = datetime(now.year, now.month, now.day)
    return date_

def parse_increase(increase):
    """
    increase: '\d' (str)
    今日の日付にincrease分の日数を加算したdatetimeオブジェクトを返す
    """
    now = datetime.now()
    return datetime(now.year, now.month, now.day) + timedelta(days=int(increase))

def parse_time(timestr):
    """
    timestr: (str)
        'HH:MM:SS' or
        'HH:MM' or
        'seconds'

    timedeltaオブジェクトに変換して返す
    """
    re_time = re.compile(r'^\d+:\d+:\d+$|^\d+:\d+$|^\d+$')
    time_ = None

    if re_time.match(timestr):
        # 'HH:MM:SS' or 'HH:MM' or 秒数
        t = [int(i) for i in timestr.split(':')]
        if len(t) == 3:
            time_ = timedelta(seconds=(t[0] * 3600) + (t[1] * 60) + t[2])
        elif len(t) == 2:
            time_ = timedelta(seconds=(t[0] * 3600) + (t[1] * 60))
        elif len(t) == 1:
            time_ = timedelta(seconds=t[0])

    return time_

def parse_time_delta(timestr_delta):
    """
    timestr: (str)
        'HH:MM:SS[+-]' or
        'HH:MM[+-]' or
        'seconds[+-]

    timedeltaオブジェクトに変換して返す
    """
    re_delta = re.compile(r'^([\w:]+)([+-])$')
    time_ = None

    m = re_delta.match(timestr_delta)
    if m:
        timestr, sign = m.group(1, 2)
        time_ = parse_time(timestr)

    if time_ and sign == '-':
        time_ *= -1

    return time_
