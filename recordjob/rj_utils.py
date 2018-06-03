# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import re
import time

def is_past(time):
    """
    引数で渡されたdatetimeオブジェクトが
    現在時刻より過去の場合にTrueを返す
    """
    current = datetime.now()
    if time < current:
        return True
    else:
        return False

def parse_channel(s_ch):
    """
    チャンネル番号をパース
    """
    re_ch = re.compile(r'^\d+$')
    if not re.match(re_ch, s_ch):
        return ''

    return s_ch

def parse_time(s_time):
    """
    'HH:MM:SS' or 'HH:MM' or 秒数を引数として受け取り、
    当日00:00:00からの差分としてtimedeltaオブジェクトとして返す
    """
    re_time = re.compile(r'^\d+:\d+:\d+|^\d+:\d+|\d+')
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

    current = datetime.now()
    if current.hour < dateline:
        # 現在時刻が基準時刻未満の場合は前日とみなす
        # ex) dateline: 5, n.hour: 2 の場合は前日の26時扱い
        current -= timedelta(days=1)

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
            offset = wdaynum.get(s_date.lower()) - current.weekday()

            # ex) 日曜日の25:00(月曜日の1:00)に「日曜日26:00開始」の
            #     録画予約を入れるとした場合
            if current.hour < dateline and offset == 1:
                # 現在時刻がdateline時までは当日扱いとする。
                offset = 0

            if offset < 0:
                # next week
                offset += 7

            date = (
                datetime(
                    current.year, current.month, current.day
                ) + timedelta(days=offset)
            )

        elif re.match(re_date, s_date):
            # YYYY/MM/DD or MM/DD or DD
            d = s_date.split('/')
            if len(d) == 3:
                year, month, day = map(int, d)
            elif len(d) == 2:
                month, day = map(int, d)
                year = current.year
            else:
                day = int(d[0])
                year = current.year
                month = current.month
            date = datetime(year, month, day)

        elif re.match(re_today, s_date):
            # today
            date = datetime(current.year, current.month, current.day)

        elif re.match(re_plus, s_date):
            # +n day
            offset = int(re.match(re_plus, s_date).group(1))
            date = (
                datetime(
                    current.year,
                    current.month,
                    current.day
                ) + timedelta(days=offset)
            )

    except ValueError:
        pass

    return date

def eval_dateline(time, dateline):
    """
    datetimeオブジェクトtimeに対し、datalineを加味した結果の
    wday, mon, day, hourを返す
    """
    if time.hour >= dateline:
        wday = time.strftime("%a")
        mon  = int(time.strftime("%m"))
        day  = int(time.strftime("%d"))
        hour = int(time.strftime("%H"))
    else:
        # 24時以降、datelineまでを当日扱いに
        wday = (time - timedelta(days=1)).strftime("%a")
        mon = int((time - timedelta(days=1)).strftime("%m"))
        day = int((time - timedelta(days=1)).strftime("%d"))
        hour = int(time.strftime("%H")) + 24
    return (wday, mon, day, hour)

def print_joblist(jobinfo, chinfo={}, header=None, dateline=0, wormup=0):
    """
    ジョブの配列を受け取り一覧表示する
    """
    if header:
        print(header)
    else:
        print('ID    Ch             Title                    Start           walltime user     queue')

    prev_wday = ''
    for j in jobinfo:
        # 表示用に録画開始時刻マージン分を加算
        begin = j.get('rec_begin') + timedelta(seconds=wormup)

        wday, mon, day, hour = eval_dateline(begin, dateline)

        # ジョブ開始時刻
        starttime = '{} {:>2}/{:<2} {:0>2}:{:0>2}'.format(
            wday,
            mon,
            day,
            hour,
            begin.minute)

        if wday != prev_wday:
            print('----- -------------- ------------------------ --------------- -------- -------- -----')

        prev_wday = wday

        # ジョブのチャンネル番号を元に対応する局名を取得
        chnum = int(j.get('channel'))
        chname = chinfo.get(chnum, '')
        s_elapse = ''
        s_walltime = ''

        # Walltimeを取得
        # FIXME:
        # Torque環境は'Resource_List.walltime'属性を使用していたため
        # 'walltime'属性が未実装
        walltime = j.get('walltime')
        if walltime:
            walltime = walltime.total_seconds() 
            s_walltime = '{:02}:{:02}:{:02}'.format(
                int(walltime / 3600),
                int(walltime % 3600 / 60),
                int(walltime % 60),
            )

        # 実行中のジョブの経過時間を取得
        elapse = j.get('elapse')
        if elapse:
            s_elapse = '{:02}:{:02}:{:02}'.format(
                int(elapse.total_seconds() / 3600),
                int(elapse.total_seconds() % 3600 / 60),
                int(elapse.total_seconds() % 60),
            )

        # ジョブの状態を取得
        state = j.get('record_state', '')
        if state == 'Waiting':
            # Waiting表示がうるさいので削る
            state = ''
        if j.get('alert'):
            state = ' '.join((j.get('alert'), state))

        print(
            '{:5} {:>3} {:10} {:24} {} {} {:8} {:5} {} {}'.format(
                j.get('rj_id', ''),
                chnum,
                chname,
                j.get('rj_title', ''),
                starttime,
                s_walltime,
                j.get('user', ''),
                j.get('tuner', ''),
                state,
                s_elapse,
            )
        )

def print_job_information(jobinfo, chinfo={}, dateline=0, wormup=0):
    """
    ジョブの配列を受け取り詳細情報を表示する
    """
    for j in jobinfo:
        # 表示用に録画開始時刻マージン分を加算
        begin = j.get('rec_begin') + timedelta(seconds=wormup)
        end = j.get('rec_end') + timedelta(seconds=wormup)

        b_wday, b_mon, b_day, b_hour = eval_dateline(begin, dateline)
        e_wday, e_mon, e_day, e_hour = eval_dateline(begin, dateline)

        # ジョブ開始時刻
        starttime = '{} {:>2}/{:<2} {:0>2}:{:0>2}:{:0>2}'.format(
            b_wday,
            b_mon,
            b_day,
            b_hour,
            begin.minute,
            begin.second)

        # ジョブ終了時刻
        endtime = '{} {:>2}/{:<2} {:0>2}:{:0>2}:{:0>2}'.format(
            e_wday,
            e_mon,
            e_day,
            e_hour,
            end.minute,
            end.second)

        chnum = int(j.get('channel'))
        chname = chinfo.get(chnum, '')
        s_elapse = None

        # 実行中のジョブの経過時間を取得
        elapse = j.get('elapse')
        if elapse:
            s_elapse = '{:02}:{:02}:{:02}'.format(
                int(elapse / 3600),
                int(elapse / 60),
                int(elapse % 60))


        print('Title:', j.get('title'))
        print('  Job Id:          ', j.get('JID'))
        print('  Channel number:  ', chnum)
        print('  Channel name:    ', chname)
        print('  Start:           ', starttime)
        print('  End:             ', endtime)
        print('  Walltime:        ', j.get('Resource_List.walltime'))
        print('  Elapse time:     ', s_elapse)
        print('  Job execute time:', j.get('Execution_Time'))
        print('  Job create time: ', j.get('ctime'))
        print('  Job modify time: ', j.get('mtime'))
        print('  Execute host:    ', j.get('exec_host'))
        print('  Owner:           ', j.get('euser'))
        print('  Group:           ', j.get('egroup'))
        print('  Queue:           ', j.get('queue'))
        print('  State:           ', j.get('record_state'))
        print('  Alert:           ', j.get('alert'))
