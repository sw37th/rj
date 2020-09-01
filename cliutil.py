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

def parse_start_time(datestr, timestr, wormup_sec=30):
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
        ジョブがスタートしてから実際に録画開始されるまでタイムラグがあるため
        指定時刻よりwormup_sec秒だけ早くジョブを開始する。
    """
    date_ = parse_date(datestr)
    time_ = parse_time(timestr)

    begin = date_ + time_ - wormup_sec
    return begin

def parse_date(datestr):
    """
    datestr: (str)
        '[YYYY/]MM/DD or
        'sun|mon|tue|wed|thu|fri|sat' or
        'today' or
        '+n'

    datetimeオブジェクトに変換して返す
    """
    date = None
    re_date = re.compile(r'^\d{4}/\d{1,2}/\d{1,2}$|^\d{1,2}/\d{1,2}$')
    re_wday = re.compile(r'^sun$|^mon$|^tue$|^wed$|^thu$|^fri$|^sat$', re.I)
    re_today = re.compile(r'^today$', re.I)
    re_increase = re.compile(r'^\+(\d+)$')
    now = datetime.now()

    if re_date.match(datestr):
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
            date = datetime(year, month, day)
        except ValueError:
            pass

    elif re_wday.match(datestr):
        wdaynum = {
            'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3,
            'fri': 4, 'sat': 5, 'sun': 6}
        offset = wdaynum.get(datestr.lower()) - now.weekday()
        if offset < 0:
            # next week
            offset += 7
        date = datetime(now.year, now.month, now.day) + timedelta(days=offset)

    elif re_today.match(datestr):
        date = datetime(now.year, now.month, now.day)

    elif re_increase.match(datestr):
        increase = int(re_increase.match(datestr).group(1))
        date = datetime(now.year, now.month, now.day) + timedelta(days=increase)

    return date

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
