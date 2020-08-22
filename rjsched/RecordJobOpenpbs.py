from copy import deepcopy
from datetime import datetime, timedelta
from subprocess import run, PIPE, CalledProcessError, TimeoutExpired
from textwrap import dedent
import json
import os
import re
import rjsched
import sys

class RecordJobOpenpbs(rjsched.RecordJob):
    def __init__(self):
        super().__init__()
        pbsexec = '/work/pbs/bin/'
        self.name = 'RecordJobOpenpbs'
        self.qstat = [pbsexec + 'qstat', '-f', '-F', 'json']
        self.pbsnodes = [pbsexec + 'pbsnodes', '-a', '-F', 'json']
        self.qsub = [pbsexec + 'qsub']
        self.qdel = [pbsexec + 'qdel']
        self.qalter = [pbsexec + 'qalter']
        self.logdir = '/home/autumn/log'
        self.joblist = []

    def __str__(self):
        return self.name

    def _run_command(self, command, _input=None):
        """
        コマンドを実行し、CompletedProcessオブジェクトを返す
        """
        try:
            proc = run(
                command,
                input=_input,
                stdout=PIPE,
                stderr=PIPE,
                universal_newlines=True,
                timeout=self.comm_timeout,
                check=True,)
        except (TimeoutExpired, CalledProcessError) as err:
            print('{} failed: {}'.format(command[0], err))
            sys.exit(1)
        return proc

    def _get_tuner_num(self):
        """
        利用可能なノードのカスタムリソース'tt'、'bs'を集計する
        """
        tuners = {'tt': 0, 'bs': 0}

        available = re.compile(r'free|job-busy')
        proc = self._run_command(self.pbsnodes)
        nodes = json.loads(proc.stdout).get('nodes', {})
        for v in nodes.values():
            if available.match(v.get('state', '')):
                resources = v.get('resources_available', {})
                tuners['tt'] += int(resources.get('tt', 0))
                tuners['bs'] += int(resources.get('bs', 0))
        return tuners

    def _check_tuner_resource(self):
        """
        チューナーの空き具合をチェックする
        最大同時録画数を超過しているジョブには警告をつける
        """
        msg = 'Out of Tuners. Max: {}'
        tuners = self._get_tuner_num()
        stack = {'tt': [], 'bs': []}

        for job in self.joblist:
            _type = job.get('tuner')
            if len(stack.get(_type)) < tuners.get(_type):
                # チューナーに空きがある
                stack.get(_type).append(job)
            else:
                # ガベージコレクト
                for stacked_job in stack.get(_type):
                    # stack内のジョブから録画終了しているものを削除
                    if job.get('rec_begin') > stacked_job.get('rec_end'):
                        stack.get(_type).remove(stacked_job)
                # 改めてチューナーの空きを確認
                if len(stack.get(_type)) < tuners.get(_type):
                    # 空きがある
                    stack.get(_type).append(job)
                else:
                    stack.get(_type).append(job)
                    for stacked_job in stack.get(_type):
                        # 現時点でstackに積まれているジョブ全てに警告を追加
                        stacked_job['alert'] = msg.format(tuners.get(_type))

    def _fetch_joblist(self):
        """
        qstatコマンドの出力から、ジョブごとに下記の情報を取得し
        self.joblist[]に詰める

        'rj_id':        OpenPBSのジョブID (str)
        'channel':      チャンネル番号 (str)
        'rj_title':     番組名 (str)
        'record_state': ジョブの状態 (str)
        'tuner':        地上波(tt) or 衛星放送(bs) (str)
        'user':         ジョブのオーナー (str)
        'group':        ジョブのグループ (str)
        'exec_host':    実行中のジョブのみ。ジョブの実行ホスト (str)
        'rec_begin':    録画開始時刻 (datetime)
        'rec_end':      録画終了時刻 (datetime)
        'walltime':     録画時間 (timedelta)
        'elapse':       実行中のジョブのみ。録画開始からの経過時間 (timedelta)
        'qtime':        ジョブのキュー追加時刻 (datetime)
        'ctime':        ジョブの作成時刻 (datetime)
        'mtime':        ジョブをMoMが最後にモニタした時刻 (datetime)
        'alert':        警告メッセージ (str)
        """
        # 同一インスタンスで複数回呼ばれた際に古い情報を返さないよう毎回クリアする
        self.joblist.clear()
        current = datetime.now()

        proc = self._run_command(self.qstat)
        jobs = json.loads(proc.stdout).get('Jobs', {})
        for k, v in jobs.items():
            # ジョブID、チャンネル番号、番組名
            job = {'rj_id': k.split('.')[0]}
            job['rj_title'], job['channel'] = v.get('Job_Name').split('.', 1)

            # 録画時間
            wt_h, wt_m, wt_s = [
                int(i) for i in v.get('Resource_List').get('walltime').split(':')]
            job['walltime'] = timedelta(hours=wt_h, minutes=wt_m, seconds=wt_s)

            # ジョブの状態、録画開始時刻、録画終了時間、録画開始からの経過時間
            state = v.get('job_state')
            if state == "R":
                # running
                job['rec_begin'] = datetime.strptime(
                    v.get('etime'), "%a %b %d %H:%M:%S %Y")
                job['elapse'] = current - job['rec_begin']
                job['exec_host'] = v.get('exec_host').split('/')[0]
            else:
                # waiting
                job['rec_begin'] = datetime.strptime(
                    v.get('Execution_Time'), "%a %b %d %H:%M:%S %Y")
            job['rec_end'] = job['rec_begin'] + job['walltime']
            job['record_state'] = self.job_state.get(state)

            # 地上波(tt) or 衛星放送(bs)
            job['tuner'] = [k for k in v.get('Resource_List').keys()
                if k == 'tt' or k == 'bs'][0]

            # ジョブのオーナー、ジョブのグループ、ジョブの実行ホスト
            job['user'] = v.get('euser')
            job['group'] = v.get('egroup')

            # qtime, ctime, mtime
            job['qtime'] = datetime.strptime(
                v.get('qtime'), "%a %b %d %H:%M:%S %Y")
            job['ctime'] = datetime.strptime(
                v.get('ctime'), "%a %b %d %H:%M:%S %Y")
            job['mtime'] = datetime.strptime(
                v.get('mtime'), "%a %b %d %H:%M:%S %Y")

            # alert
            job['alert'] = ''

            self.joblist.append(job)

        # 録画開始時刻で昇順にソート
        self.joblist = sorted(
            self.joblist, key=lambda x:x['rec_begin'])

    def get_job_info(self, jid='', date=None,):
        """
        ジョブ情報をリストに詰め、呼び出し元に返す
        下記の引数が指定されている場合はそのジョブ情報のみ抽出する
        jid:  ジョブID (str)
        date: ジョブの実行日 (datetime)
        """

        # ジョブ情報リスト取得
        self._fetch_joblist()

        # 最大同時録画数のチェック
        self._check_tuner_resource()

        if jid:
            # 指定されたジョブIDの情報のみ抽出
            joblist = [i for i in self.joblist if i['rj_id'] in jid]
        elif date:
            # 指定された日に録画を開始するジョブの情報のみ抽出
            nextday = date + timedelta(days=1)
            joblist = [
                i for i in self.joblist
                    if i['rec_begin'] >= date and i['rec_begin'] < nextday]
        else:
            # 全ジョブ
            joblist = deepcopy(self.joblist)

        return joblist

    def add(self, ch, title, begin, rectime, repeat=''):
        """
        ジョブをサブミットする
        ch:      チャンネル番号(str)
        title:   番組名(str)
        begin:   開始時間(datetime)
        rectime: 録画時間(timedelta)
        repeat:  繰り返しフラグ(str)

        qsubコマンドの出力するジョブIDからID番号のみを切り出して返す
        """

        recpt1_args = \
            '${{PBS_JOBNAME##*.}} - {}/${{PBS_JOBNAME}}.'\
            '$(date +%Y%m%d_%H%M.%S).${{PBS_JOBID%.*}}.ts'.format(self.recdir)
        recpt1 = self.recpt1[:]
        if self._is_bs(ch):
            recpt1.extend(['--lnb 15', recpt1_args])
            tuner = 'bs'
        else:
            recpt1.append(recpt1_args)
            tuner = 'tt'

        jobexec = ' '.join(recpt1)
        qsub = self.qsub[:] + [
                '-N', '{}.{}'.format(title, ch),
                '-a', begin.strftime('%Y%m%d%H%M.%S'),
                '-l', 'walltime={}'.format(str(int(rectime.total_seconds()))),
                '-l', '{}=1'.format(tuner),
                '-j', 'oe',
                '-o', self.logdir,
                '-W', 'umask=222',
                '-',]

        proc = self._run_command(command=qsub, _input=jobexec)
        return proc.stdout.split('.', 1)[0]

    def remove(self, jid=''):
        """
        引数で与えられたIDのジョブを削除する
        FIXME: 引数をstrではなくlistに変更して複数ジョブを一括削除

        削除したジョブ情報のリストを返す
        """
        joblist = self.get_job_info(jid)
        if joblist:
            qdel = self.qdel[:]
            qdel.append(jid)
            self._run_command(qdel)

        return joblist

    def change_begin(self, jid, begin):
        """
        録画ジョブの開始時刻を指定時刻に変更
        変更前と変更後のジョブ情報をリストに詰めて返す
        """
        joblist = self.get_job_info(jid)
        if joblist:
            qalter = self.qalter[:]
            qalter.extend(['-a', begin.strftime('%Y%m%d%H%M.%S'), jid])
            self._run_command(qalter)

            changed = self.get_job_info(jid)
            joblist.extend(changed)

        """
        joblist: [origin, changed]
        """
        return joblist

    def change_begin_delta(self, jid, delta):
        """
        録画ジョブの現在の開始時刻を基準に相対的に変更
        変更前と変更後のジョブ情報をリストに詰めて返す
        """
        joblist = self.get_job_info(jid)
        if joblist:
            begin = joblist[0].get('rec_begin') + delta
            qalter = self.qalter[:]
            qalter.extend(['-a', begin.strftime('%Y%m%d%H%M.%S'), jid])
            self._run_command(qalter)

            changed = self.get_job_info(jid)
            joblist.extend(changed)

        """
        joblist: [origin, changed]
        """
        return joblist
