from datetime import datetime, timedelta
import re
import sys

def is_future(begin):
    """
    begin: 録画開始時刻 (datetime)

    beginが現在時刻より未来の場合にTrueを返す
    """
    current = datetime.now()
    if begin > current:
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
        'HH:MM:SS' or 'HH:MM' or '秒数'
    wormup_sec: (int)
        録画開始までのマージン
        ジョブがスタートしてから実際に録画開始されるまでタイムラグがあるため
        指定時刻よりwormup_sec秒だけ早くジョブを開始する。
    """
    date_ = parse_date(datestr)
    time_ = parse_time(timestr)

    begin = date_ + time_ - wormup_sec
    return begin

def parse_time(timestr):
    """
    timestr: (str)
        'HH:MM:SS' or
        'HH:MM' or
        '秒数'

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
        'HH:MM:SS' or
        'HH:MM:SS+' or
        'HH:MM:SS-'
    timedeltaオブジェクトとして返す
    """
    re_delta = re.compile(r'^([\w:]+)([+-]*)$')

    m = re_delta.match(timestr_delta)
    if m:
        timestr, sign = m.group(1, 2)

    time_ = parse_time(timestr)
    if time_:
        if sign == '-':
            return -time_
        else:
            return time_
    else:
        return None

