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
    00:00:00からの差分のtimedeltaオブジェクトとして返す
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

def parse_date(s_date, dateline=0, dateonly=True):
    """
    'YYYY/MM/DD|MM/DD|DD' or
    'sun|mon|tue|wed|thu|fri|sat' or
    'today' or
    '+Nd'
    を引数として受け取り、
    'YYYY/MM/DD 00:00:00'のdatetimeオブジェクトとして返す

    dateline: 基準時刻(hour)
      ジョブの登録や表示の際、何時から何時までを当日とみなすかの
      基準となる時刻を指定する。
      dateline=5 は 05:00:00-28:59:59 を当日とみなす。
      この場合、1/2 02:00:00 は 1/1 26:00:00 となる。
      (深夜アニメ対策)

    dateonly: 
      作成したdatetimeオブジェクトにdateline時刻を反映させるか否か。
      dateonlyがFalseの場合、returnするdatetimeオブジェクトは
      'YYYY/MM/DD <dateline>:00:00'となる。
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

    if not dateonly:
        date += timedelta(seconds=dateline*3600)

    return date

def print_joblist(jobinfo, chinfo={}, header=None, dateline=0, wormup=0):
    """
    ジョブの配列を受け取り一覧表示する
    """
    if header:
        print(header)
    else:
        print(
            'ID       Ch             Title                    ' +
            'Start           walltime tuner'
        )

    prev_wday = ''
    for j in jobinfo:
        # 表示用に録画開始時刻マージン分を加算
        begin = j.get('rec_begin') + timedelta(seconds=wormup)

        # ジョブ開始時刻
        starttime = str_w_ymd_hms(begin, dateline)
        wday = starttime.split()[0]

        if wday != prev_wday:
            print(
                '-------- -------------- ------------------------ ' +
                '--------------- -------- -----'
            )

        prev_wday = wday

        # ジョブのチャンネル番号を元に対応する局名を取得
        chnum = int(j.get('channel'))
        chname = chinfo.get(chnum, '')

        # Walltimeを取得
        walltime = j.get('walltime')
        if walltime:
            s_walltime = strhms(walltime.total_seconds())
        else:
            s_walltime = ''

        # 実行中のジョブの経過時間を取得
        elapse = j.get('elapse')
        if elapse:
            s_elapse = strhms(elapse.total_seconds())
        else:
            s_elapse = ''

        # ジョブの状態を取得
        state = j.get('record_state', '')
        if state == 'Waiting':
            # Waiting表示がうるさいので削る
            state = ''
        if j.get('alert'):
            state = ' '.join((j.get('alert'), state))

        print(
            '{:8} {:>3} {:10} {:24} {} {} {:5} {} {}'.format(
                j.get('rj_id', ''),
                chnum,
                chname,
                j.get('rj_title', ''),
                starttime,
                s_walltime,
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

        # ジョブ開始時刻
        starttime = str_w_ymd_hms(begin, dateline, year=True, sec=True)

        # ジョブ終了時刻
        endtime = str_w_ymd_hms(end, dateline, year=True, sec=True)

        # Walltimeを取得
        walltime = j.get('walltime')
        if walltime:
            s_walltime = strhms(walltime.total_seconds())
        else:
            s_walltime = None

        # チャンネル番号と局名を取得
        chnum = int(j.get('channel'))
        chname = chinfo.get(chnum, '')

        # 実行中のジョブの経過時間を取得
        elapse = j.get('elapse')
        if elapse:
            s_elapse = strhms(elapse.total_seconds())
        else:
            s_elapse = None

        print('Title:', j.get('rj_title'))
        print('  Job Id:          ', j.get('rj_id'))
        print('  Channel number:  ', chnum)
        print('  Channel name:    ', chname)
        print('  Start:           ', starttime)
        print('  End:             ', endtime)
        print('  Walltime:        ', s_walltime)
        print('  Elapse time:     ', s_elapse)
        print('  Owner:           ', j.get('user'))
        print('  Group:           ', j.get('group'))
        print('  Tuner:           ', j.get('tuner'))
        print('  State:           ', j.get('record_state'))
        print('  Alert:           ', j.get('alert'))
        print('  Job execute time:', j.get('Execution_Time'))
        print('  Job create time: ', j.get('ctime'))
        print('  Job modify time: ', j.get('mtime'))
        print('  Execute host:    ', j.get('exec_host'))

def strhms(sec):
    """
    秒数を受け取ってHH:MM:SS形式の文字列を返す
    """
    hms = '{:02}:{:02}:{:02}'.format(
        int(sec / 3600),
        int(sec % 3600 / 60),
        int(sec % 60),
    )
    return hms

def str_w_ymd_hms(time, dateline=0, year=False, sec=False):
    """
    datetimeオブジェクトとdatelineを受け取り
    datelineを加味した"Wday yyyy/mm/dd HH:MM:SS"を返す
    """
    _wday, _year, _mon, _day, _hour = eval_dateline(time, dateline)

    if year:
        w_ymd = '{} {:0>4}/{:0>2}/{:0>2}'.format(_wday, _year, _mon, _day)
    else:
        w_ymd = '{} {:>2}/{:<2}'.format(_wday, _mon, _day)

    if sec:
        hms = '{:0>2}:{:0>2}:{:0>2}'.format(_hour, time.minute, time.second)
    else:
        hms = '{:0>2}:{:0>2}'.format(_hour, time.minute)

    return w_ymd + ' ' + hms

def eval_dateline(time, dateline):
    """
    datetimeオブジェクトtimeに対し、datalineを加味した結果の
    wday, year, mon, day, hourを返す
    """
    if time.hour >= dateline:
        wday = time.strftime("%a")
        year = int(time.strftime("%Y"))
        mon  = int(time.strftime("%m"))
        day  = int(time.strftime("%d"))
        hour = int(time.strftime("%H"))
    else:
        # 24時以降、datelineまでを当日扱いに
        wday = (time - timedelta(days=1)).strftime("%a")
        year = int((time - timedelta(days=1)).strftime("%Y"))
        mon  = int((time - timedelta(days=1)).strftime("%m"))
        day  = int((time - timedelta(days=1)).strftime("%d"))
        hour = int(time.strftime("%H")) + 24
    return (wday, year, mon, day, hour)
