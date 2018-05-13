# -*- coding: utf-8 -*-

from subprocess import Popen, PIPE, TimeoutExpired
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

    def _get_torque_job_info(self, target_jid=None):
        jobs = {}
        present = datetime.datetime.now()

        if target_jid:
            if not target_jid.isdigit():
                return []

            self.qstat.append(target_jid)

        # qstat -f -1でジョブ情報を取得し、２次元dictに詰める
        # jobs['jobid'][{"key": value, "key": value, ...}]
        try:
            with Popen(self.qstat,
                universal_newlines=True,
                stdout=PIPE,
                stderr=PIPE
            ) as pjob:

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
        self._check_channel_resource(job_array)

        return job_array

    def _check_channel_resource(self, job_array):
        # チャンネルリソースの空き具合をチェックする
        queue_info = self._get_queue_info()

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

    def _get_queue_info(self):
        nodes = {}
        queue_info = {}

        # pbsnodes -qの出力から以下の情報を取得する。
        # ノード名
        # properties: そのノードの所属するキュー名
        # np:         チューナー数
        # state:      ノードの状態
        try:
            with Popen(self.pbsnodes,
                universal_newlines=True,
                stdout=PIPE,
                stderr=PIPE
            ) as pnodes:
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

    def mod_begintime(self, jobinfo, date=None, time_delta=None):
        """
        録画ジョブの開始時間を変更する。
        """

        if date:
            begin = date
        elif time_delta:
            begin = jobinfo[0]['rec_begin'] + time_delta

        # make qalter argument
        at = '{_year:>4}{_mon:0>2}{_day:0>2}{_hour:0>2}{_min:0>2}.{_sec:0>2}'.format(
            _year=begin.year,
            _mon=begin.month,
            _day=begin.day,
            _hour=begin.hour,
            _min=begin.minute,
            _sec=begin.second)

        self.qalter.extend([at, jobinfo[0]['JID']])

        # ジョブ開始時間を変更
        try:
            with Popen(self.qalter, universal_newlines=True) as modify:
                modify.wait(timeout=self.comm_timeout)
        except (OSError, ValueError, TimeoutExpired) as err:
            print('cannot modify job: {0}'.format(err))

    def get_channel_info(self):
        # チャンネル番号と局名の対応表をYAMLファイルから取得して返す
        try:
            with open(self.channel_file) as f:
                chinfo = yaml.load(f)
        except (PermissionError, FileNotFoundError) as err:
            return None

        return chinfo

    def get_job_info(self, date=None, jid=None):
        # 録画ジョブ情報を取得して配列として返す

        jobinfo = self._get_torque_job_info(jid)

        if date:
            # dateで指定された日のジョブのみを配列に詰め直す
            nextday = date + datetime.timedelta(days=1)
            jobinfo = [
                i for i in jobinfo 
                    if i['rec_begin'] >= date and i['rec_begin'] < nextday
            ]

        return jobinfo

    def add(self, ch, title, begin, rectime):
        """
        ジョブスケジューラに録画ジョブを追加する
        """

        if int(ch) < 100:
            # for terrestrial television
            queue = queuename['terrestrial']
            lnb = ''
        else:
            # for broadcasting satellite
            queue = queuename['satellite']
            lnb = '--lnb 15'

        # ジョブスクリプトファイルに渡すジョブ開始時刻、実行時間を生成
        at = '{_year:0>4}{_month:0>2}{_day:0>2}{_hour:0>2}{_min:0>2}.{_sec:0>2}'.format(
            _year=begin.year,
            _month=begin.month,
            _day=begin.day,
            _hour=begin.hour,
            _min=begin.minute,
            _sec=begin.second)
        walltime = '{_hour:0>2}:{_min:0>2}:{_sec:0>2}'.format(
            _hour=int((rectime.seconds / 3600) + (rectime.days * 24)),
            _min=int((rectime.seconds / 60) % 60),
            _sec=int(rectime.seconds % 60))

        # ジョブスクリプトファイルを生成
        jobscript = """#!/bin/sh
#PBS -q {_queue}
#PBS -N {_ch}.{_title}
#PBS -a {_at}
#PBS -l walltime={_wt}
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
                f.write(
                    jobscript.format(
                        _queue=queue,
                        _ch=ch,
                        _title=title,
                        _at=at,
                        _wt=walltime,
                        _logdir=self.logdir,
                        _recdir=self.recdir,
                        _recpt1=self.recpt1_path,
                        _lnb=lnb
                    )
                )
        except (PermissionError, FileNotFoundError) as err:
            print('cannot create jobscript: {0}'.format(err))
            return ''

        try:
            with Popen(
                (self.qsub, filename),
                universal_newlines=True,
                stdout=PIPE,
                stderr=PIPE
            ) as submit:
                # waiting for complete of job submit
                submit.wait(timeout=self.comm_timeout)

                # get submitted job's ID
                stdout_data, stderr_data = submit.communicate()
                jid = re.match(r'^(\d+)\.', stdout_data).group(1)

        except (OSError, ValueError, TimeoutExpired) as err:
            print('cannot submit job: {0}'.format(err))
            return ''

        return jid
