# -*- coding: utf-8 -*-

import subprocess
import re
import datetime
import time
import yaml

# torque commands
qstat_path = '/usr/local/torque/bin/qstat'
pbsnodes_path = '/usr/local/torque/bin/pbsnodes'
qsub_path = '/usr/local/torque/bin/qsub'
qalter_path = '/usr/local/torque/bin/qalter'
recpt1_path = '/usr/local/bin/recpt1'
scriptdir = '/home/autumn/jobsh'
logdir = '/home/autumn/log'
recdir = '/home/autumn/rec'
channel_file = '/home/autumn/work/rj/channel.yml'
wormup_offset_s = 10
dateline_offset_h = 5
comm_timeout = 10
queuename = {
    'satellite': 'bs',
    'terrestrial': 'tt',
}

class RecordJobTorque:
    def __init__(self):
        self.qstat = [qstat_path, '-f', '-1' ]
        self.pbsnodes = [pbsnodes_path, '-a' ]
        self.qsub = qsub_path
        self.qalter = [qalter_path, '-a' ]
        self.wormup_offset_s = wormup_offset_s
        self.dateline_offset_h = dateline_offset_h
        self.comm_timeout = comm_timeout
        self.recpt1_path = recpt1_path
        self.scriptdir = scriptdir
        self.logdir = logdir
        self.recdir = recdir
        self.channel_file = channel_file
        self.job_state = {
            'C': "Completed",
            'E': "Exiting",
            'H': "on Hold",
            'Q': "Queued",
            'R': "Recording",
            'T': "Moved",
            'W': "",
            'S': "Suspend",
        }

    def get_job_info(self, target_jid=None):
        jobs = {}
        present = datetime.datetime.now()

        if target_jid:
            if not target_jid.isdigit():
                return []

            self.qstat.append(target_jid)

        # qstat -f -1でジョブ情報を取得し、２次元dictに詰める
        # jobs['jobid'][{"key": value, "key": value, ...}]
        try:
            with subprocess.Popen(self.qstat,
                                    universal_newlines=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE) as pjob:

                re_jobid = re.compile(r'^Job Id:\s*(\d+)\.')
                re_equal = re.compile(r'^\s+([\w.]+) = (.+$)')

                for jinfo in pjob.stdout:
                    if re.match(re_jobid, jinfo):
                        # a job informations begin here
                        jid = re.match(re_jobid, jinfo).group(1)
                        jobs[jid] = {}
                        jobs[jid]['JID'] = jid
                        continue

                    if re.match(re_equal, jinfo):
                        # set key and value to jobs['jobid']
                        (jkey, jval) = re.match(re_equal, jinfo).group(1,2)
                        jobs[jid][jkey] = jval

        except (OSError, ValueError) as err:
            print('cannot get job information: {0}'.format(err))
            return []

        # 不足する情報を追加
        for jid in jobs.keys():
            if 'Execution_Time' in jobs[jid]:
                # 実行開始前(State: W)のジョブ。
                # 実行開始時間はqstat -fのExectiton_Timeから取得できる。
                # ex. "Tue Mar 15 23:59:50 2016"
                jobs[jid]['rec_begin'] = datetime.datetime.strptime(
                                            jobs[jid]['Execution_Time'],
                                            "%a %b %d %H:%M:%S %Y")
            elif 'start_time' in jobs[jid]:
                # 実行中(State: R)、実行終了(State: C)のジョブ。
                # 実行開始時間はqstat -fのstart_timeから取得できる。
                # フォーマットはExecution_Timeに同じ。
                jobs[jid]['rec_begin'] = datetime.datetime.strptime(
                                            jobs[jid]['start_time'],
                                            "%a %b %d %H:%M:%S %Y")
            else:
                # ここに来るケースあるかしら？
                jobs[jid]['rec_begin'] = present;

            # ジョブ終了時間をjobs[jid]['rec_end']に登録する。
            # ジョブ開始時間 + Resource_List.walltime
            (wt_h, wt_m, wt_s) = list(map(int, jobs[jid]['Resource_List.walltime'].split(':')))
            jobs[jid]['rec_end'] = (jobs[jid]['rec_begin'] +
                                    datetime.timedelta(hours=wt_h, minutes=wt_m, seconds=wt_s))

            # タイトル、チャンネル番号を登録する
            (jobs[jid]['channel'], jobs[jid]['title']) = jobs[jid]['Job_Name'].split('.', 1)

            # qstatのjob_stateをわかりやすい表記に
            jobs[jid]['record_state'] = self.job_state[jobs[jid]['job_state']]

            if jobs[jid]['job_state'] == 'R':
                # 録画開始からの経過時間を算出
                elapse = (present - jobs[jid]['rec_begin']).seconds
                # record_stateに経過時間と録画実行ホストを追記
                jobs[jid]['record_state'] = (
                    jobs[jid]['record_state'] +
                    "({0:02}:{1:02}:{2:02})@{3}".format(
                        int(elapse/60/60),
                        int(elapse/60),
                        elapse%60,
                        re.sub('/.*$', '', jobs[jid]['exec_host'])))

        job_array = [jobs[x] for x in sorted(jobs.keys())]
        job_array = sorted(job_array, key=lambda j: j['rec_begin'])
        self.chech_channel_resource(job_array)

        return job_array

    def chech_channel_resource(self, job_array):
        # チャンネルリソースの空き具合をチェックする
        queue_info = self.get_queue_info()

        for job in job_array:
            if job['job_state'] == 'C':
                continue
            if (len(queue_info[job['queue']]['jobs']) <
                queue_info[job['queue']]['ch_max']):
                # チャンネルの空きがある
                # queue_info[job['queue']]['jobs']にこのジョブを登録
                queue_info[job['queue']]['jobs'].append(job)
            else:
                # ガベージコレクト
                for old_job in queue_info[job['queue']]['jobs']:
                    # queue_info[job['queue']]['jobs']に残っているジョブから
                    # 録画終了しているものを削除
                    if job['rec_begin'] > old_job['rec_end']:
                        queue_info[job['queue']]['jobs'].remove(old_job)

                # 改めてチャンネルの空き確認
                if (len(queue_info[job['queue']]['jobs']) <
                    queue_info[job['queue']]['ch_max']):
                    # チャンネルの空きがある
                    # queue_info[job['queue']]['jobs']にこのジョブを登録
                    queue_info[job['queue']]['jobs'].append(job)
                else:
                    job['alart'] = 'NoResource'

    def get_queue_info(self):
        nodes = {}
        queue_info = {}

        # pbsnodes -qの出力から以下の情報を取得する。
        # ノード名
        # properties: そのノードの所属するキュー名
        # np:         チューナー数
        # state:      ノードの状態
        try:
            with subprocess.Popen(self.pbsnodes,
                                    universal_newlines=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE) as pnodes:
                re_ninfo = re.compile(r'^\s+(state|np|properties) = (\S+)')
                re_nname = re.compile(r'^\S+')
                for ninfo in pnodes.stdout:
                    if re.match(re_nname, ninfo):
                        # a node informations begin here
                        n = ninfo.rstrip()
                        nodes[n] = {}
                        continue
                    if re.match(re_ninfo, ninfo):
                        (key, value) = re.search(re_ninfo, ninfo).group(1, 2)
                        nodes[n][key] = value
        except (OSError, ValueError) as err:
            print('cannot get node information: {0}'.format(err))
            return None

        # キューごとに、そのキューに所属するノードとチャンネル数を集計する。
        for node in nodes.values():
            if re.search(r'(offline|down)', node['state']):
                # 稼動状態にないノードは除外
                continue

            if not node['properties'] in queue_info:
                queue_info[node['properties']] = {}
                queue_info[node['properties']]['ch_max'] = 0
                queue_info[node['properties']]['jobs'] = []

            queue_info[node['properties']]['ch_max'] += int(node['np'])

        return queue_info

    def mod_begintime(self, jid, delta):
        # 録画ジョブの開始時間を変更する。
        # +HH:MM:SS or -HH:MM:SS
        jobinfo = self.get_job_info(jid)
        if jobinfo is None:
            print('JID: {} not found'.format(jid))
            return

        # 変更前のジョブ情報を表示
        self._print_jobinfo(jobinfo)

        re_delta = re.compile(r'^([+-])([\w:]+)')
        if re.match(re_delta, delta):
            (delta_sign, delta_time) = re.match(re_delta, delta).group(1, 2)

            if delta_sign == '+':
                jobinfo[0]['rec_begin'] += self.analyze_time(delta_time)
            else:
                jobinfo[0]['rec_begin'] -= self.analyze_time(delta_time)

        # make qalter argument
        at = '{_year:>4}{_mon:0>2}{_day:0>2}{_hour:0>2}{_min:0>2}.{_sec:0>2}'.format(
        _year=jobinfo[0]['rec_begin'].year,
        _mon=jobinfo[0]['rec_begin'].month,
        _day=jobinfo[0]['rec_begin'].day,
        _hour=jobinfo[0]['rec_begin'].hour,
        _min=jobinfo[0]['rec_begin'].minute,
        _sec=jobinfo[0]['rec_begin'].second)
        self.qalter.extend([at, jid])

        # ジョブ開始時間を変更
        try:
            with subprocess.Popen(self.qalter, universal_newlines=True) as modify:
                modify.wait(timeout=self.comm_timeout)
        except (OSError, ValueError, TimeoutExpired) as err:
            print('cannot modify job: {0}'.format(err))
            return

        # 変更後のジョブ情報を表示
        jobinfo = self.get_job_info(jid)
        self._print_jobinfo(jobinfo, "(Modified to)")

        return

    def get_channel_info(self):
        # チャンネル番号と局名の対応表を取得して返す
        try:
            with open(self.channel_file) as f:
                chinfo = yaml.load(f)
        except (PermissionError, FileNotFoundError) as err:
            return None

        return chinfo

    def show(self, date=None, jid=None, header=None):
        # 録画ジョブを一覧表示

        jobinfo = self.get_job_info(jid)

        if date:
            nextday = date + datetime.timedelta(days=1)
            # DEBUG
            print('date', date)
            print('nextday', nextday)
            jobinfo = [
                i for i in jobinfo 
                    if i['rec_begin'] >= date and i['rec_begin'] < nextday]

        #self._print_jobinfo(jobinfo, header)
        return jobinfo

    def _print_jobinfo(self, jobinfo, header=None):
        # チャンネル番号と局名の対応表を取得
        chinfo = self.get_channel_info()

        if header:
            print(header)
        else:
            print('ID    Ch             Title                    Start           walltime user     queue')

        prev_wday = ''
        for j in jobinfo:
            # 表示用に録画開始時刻マージン分を加算したdatetimeオブジェクトを作成
            begin = j['rec_begin'] + datetime.timedelta(seconds=self.wormup_offset_s)

            if begin.hour >= self.dateline_offset_h:
                wday = begin.strftime("%a")
                mon  = int(begin.strftime("%m"))
                day  = int(begin.strftime("%d"))
                hour = int(begin.strftime("%H"))
            else:
                # 24時以降、dateline_offset_hまでの録画ジョブを当日扱いに
                wday = (begin - datetime.timedelta(days=1)).strftime("%a")
                mon = int((begin - datetime.timedelta(days=1)).strftime("%m"))
                day = int((begin - datetime.timedelta(days=1)).strftime("%d"))
                hour = int(begin.strftime("%H")) + 24

            if wday != prev_wday:
                print('----- -------------- ------------------------ --------------- -------- -------- -----')

            prev_wday = wday

            # チャンネル番号を元に局名を取得
            chnum = int(j['channel'])
            chname = ""
            if chinfo is not None:
                if chnum in chinfo['channel']:
                    chname = chinfo['channel'][chnum]

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

        return

    def analyze_time(self, str_time):
        # 'HH:MM:SS' or 'HH:MM' or 秒数 or 'now' を引数として受け取り、
        # 00:00:00からの差分としてtimedeltaオブジェクトに格納して返す

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
            present = datetime.datetime.now()
            # 後で除算される分のwormup_offset_sもあらかじめ足しておく
            time = (datetime.timedelta(
                    seconds=(present.hour*60*60)+(present.minute*60)+present.second +
                    self.wormup_offset_s,
                    microseconds=present.microsecond))

        return time

    def analyze_date(self, str_date):
        # "YYYY/MM/DD" or "MM/DD" or "DD" or "sun|mon|tue|wed|thu|fri|sat"
        re_wday = re.compile(r'^sun$|^mon$|^tue$|^wed$|^thu$|^fri$|^sat$', re.I)
        re_date = re.compile(r'^\d{4}/\d{1,2}/\d{1,2}$|^\d{1,2}/\d{1,2}$|^\d{1,2}$')
        re_today = re.compile(r'^today$', re.I)
        re_plus = re.compile(r'^\+(\d+)d$', re.I)

        present = datetime.datetime.now()
        # dateline_offset_h時未満なら当日と見なす
        if present.hour < self.dateline_offset_h:
            present -= datetime.timedelta(days=1)

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
            today = present.weekday()
            offset = wdaynum[str_date.lower()] - today
            if offset < 0:
                offset += 7
            date = (datetime.datetime(present.year, present.month, present.day) +
                    datetime.timedelta(days=offset))

        elif re.match(re_date, str_date):
            # YYYY/MM/DD or MM/DD or DD
            d = str_date.split('/')
            if len(d) == 3:
                (year, month, day) = map(int, d)
            elif len(d) == 2:
                (month, day) = map(int, d)
                year = present.year
            else:
                day = int(d[0])
                year = present.year
                month = present.month
            date = datetime.datetime(year, month, day)
        elif re.match(re_today, str_date):
            # today
            date = datetime.datetime(present.year, present.month, present.day)
        elif re.match(re_plus, str_date):
            # +n day
            n = re.match(re_plus, str_date).group(1)
            date = (datetime.datetime(present.year, present.month, present.day) +
                    datetime.timedelta(days=int(n)))

        return date

    def add(self, ch, title, date, time, wt='00:29:00'):
        present = datetime.datetime.now()

        re_ch = re.compile(r'^\d+$')
        if not re.match(re_ch, ch):
            print('invalid channel({0})'.format(ch))
            return

        if int(ch) < 100:
            # for terrestrial television
            queue = queuename['terrestrial']
            lnb = ''
        else:
            # for broadcasting satellite
            queue = queuename['satellite']
            lnb = '--lnb 15'

        rec_date = self.analyze_date(date)
        if rec_date is None:
            print('invalid date({0})'.format(date))
            return

        rec_begin_time = self.analyze_time(time)
        if rec_begin_time is None:
            print('invalid time({0})'.format(time))
            return

        walltime = self.analyze_time(wt)
        if walltime is None:
            print('invalid walltime({0})'.format(wt))
            return

        rec_begin = rec_date + rec_begin_time - datetime.timedelta(seconds=self.wormup_offset_s)

        if rec_begin < present:
            # 指定された開始時刻が過ぎている
            print('start in the past?')
            #print('begin: %r,  now: %r' % (rec_begin, present))
            return

        # qsub の -a オプションに渡すジョブ開始時刻を生成
        at = '{0:0>4}{1:0>2}{2:0>2}{3:0>2}{4:0>2}.{5:0>2}'.format(
        rec_begin.year,
        rec_begin.month,
        rec_begin.day,
        rec_begin.hour,
        rec_begin.minute,
        rec_begin.second,)

        # ジョブスクリプトを生成
        jobscript = """#!/bin/sh
#PBS -q {_queue}
#PBS -N {_ch}.{_title}
#PBS -a {_at}
#PBS -l walltime={_wt_H:0>2}:{_wt_M:0>2}:{_wt_S:0>2}
#PBS -j oe
#PBS -o {_logdir}
#PBS -e {_logdir}

umask 022
_id=`echo $PBS_JOBID | awk -F'.' '{{printf("%04d", $1)}}'`
{_recpt1} {_lnb} --b25 --strip {_ch} - {_recdir}/{_title}.{_ch}.`date +%Y%m%d_%H%M.%S`.$_id.ts
"""

        filename = scriptdir + '/' + title + '.' + at + '.sh'
        try:
            with open(filename, 'w') as f:
                f.write(jobscript.format(
                _queue=queue,
                _ch=ch,
                _title=title,
                _at=at,
                _wt_H=int((walltime.seconds/60/60)+(walltime.days*24)),
                _wt_M=int((walltime.seconds/60)%60),
                _wt_S=int(walltime.seconds%60),
                _logdir=self.logdir,
                _recdir=self.recdir,
                _recpt1=self.recpt1_path,
                _lnb=lnb))
        except (PermissionError, FileNotFoundError) as err:
            print('cannot create jobscript: {0}'.format(err))
            return

        try:
            with subprocess.Popen(
                (self.qsub, filename),
                universal_newlines=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            ) as submit:
                # waiting for complete of job submit
                submit.wait(timeout=self.comm_timeout)

                # show submitted job information
                stdout_data, stderr_data = submit.communicate()
                jid = re.match(r'^(\d+)\.', stdout_data).group(1)
                self.show(jid=jid)

        except (OSError, ValueError, TimeoutExpired) as err:
            print('cannot submit job: {0}'.format(err))
            return

        return
