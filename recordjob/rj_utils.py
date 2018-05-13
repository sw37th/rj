from datetime import datetime, timedelta
import re
import time

def is_past(time):
    current = datetime.now()
    if time < current:
        return True
    else:
        return False

def parse_time(s_time):
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
            time = timedelta(seconds=(t[0] * 3600) + (t[1] * 60) + t[2])
        elif len(t) == 2:
            time = timedelta(seconds=(t[0] * 3600) + (t[1] * 60))
        elif len(t) == 1:
            time = timedelta(seconds=t[0])
    elif re.match(re_now, s_time):
        # 'now'
        n = datetime.now()
        n_sec = (n.hour * 3600) + (n.minute * 60) + n.second
        time = timedelta(seconds=n_sec, microseconds=n.microsecond)

    return time

def parse_time_delta(s_time_delta):
    """
    'HH:MM:SS' or 'HH:MM:SS+' or 'HH:MM:SS-'を引数として受け取り、
    timedeltaオブジェクトとして返す
    """
    re_delta = re.compile(r'^([\w:]+)([+-]*)$')
    if re.match(re_delta, s_time_delta):
        s_time, sign = re.match(re_delta, s_time_delta).group(1, 2)

    time = parse_time(s_time)
    if time:
        if sign == '-':
            return -time
        else:
            return time
    else:
        return None

def parse_date(s_date, dateline=0):
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
            if n.hour < dateline:
                # 現在時刻が基準時刻未満の場合は前日とみなす
                # ex) dateline: 5, n.hour: 2 の場合は前日の26時扱い
                date -= timedelta(days=1)

        elif re.match(re_plus, s_date):
            # +n day
            offset = int(re.match(re_plus, s_date).group(1))
            date = datetime(n.year, n.month, n.day) + timedelta(days=offset)
            if n.hour < dateline:
                # 現在時刻が基準時刻未満の場合は前日とみなす
                # ex) dateline: 5, n.hour: 2 の場合は前日の26時扱い
                date -= timedelta(days=1)

    except ValueError:
        pass

    if date:
        # 当日の基準時刻を修正する
        date += timedelta(seconds=(dateline * 3600))

    return date

def print_jobinfo(jobinfo, chinfo=None, header=None, dateline=0, wormup=0):

    if header:
        print(header)
    else:
        print('ID    Ch             Title                    Start           walltime user     queue')

    prev_wday = ''
    for j in jobinfo:
        # 表示用に録画開始時刻マージン分を加算
        begin = j['rec_begin'] + timedelta(seconds=wormup)

        if begin.hour >= dateline:
            wday = begin.strftime("%a")
            mon  = int(begin.strftime("%m"))
            day  = int(begin.strftime("%d"))
            hour = int(begin.strftime("%H"))
        else:
            # 24時以降、datelineまでの録画ジョブを当日扱いに
            wday = (begin - timedelta(days=1)).strftime("%a")
            mon = int((begin - timedelta(days=1)).strftime("%m"))
            day = int((begin - timedelta(days=1)).strftime("%d"))
            hour = int(begin.strftime("%H")) + 24

        if wday != prev_wday:
            print('----- -------------- ------------------------ --------------- -------- -------- -----')

        prev_wday = wday

        # チャンネル番号を元に局名を取得
        chnum = int(j['channel'])
        chname = ''
        if chinfo:
            chname = chinfo['channel'].get(chnum)

        print('{0:5} {1:>3} {2:10} {3:24} {4} {5:>2}/{6:<2} {7:0>2}:{8:0>2} {9} {10:8} {11:5} {12}'.format(
            j['JID'],
            chnum,
            chname,
            j['title'],
            wday,
            mon,
            day,
            hour,
            begin.minute,
            j['Resource_List.walltime'],
            j['euser'],
            j['queue'],
            j['record_state'],
            ),
            end='')

        if 'alart' in j:
            print(' ({0})'.format(j['alart']))
        else:
            print()
