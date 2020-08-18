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
        self.qalter = [pbsexec + 'qalter', '-a']
        self.scriptdir = '/home/autumn/jobsh'
        self.logdir = '/home/autumn/log'
        self.joblist = []
        self.tuners = {'tt': 0, 'bs': 0}

    def __str__(self):
        return self.name

    def _get_job_info_all(self):
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
        'alert':        チューナー不足の警告 (str)
        """
        current = datetime.now()

        proc = self._run_command(self.qstat)
        jobs = json.loads(proc.stdout).get('Jobs', {})
        for k, v in jobs.items():
            # ジョブID、チャンネル番号、番組名
            job = {'rj_id': k.split('.')[0]}
            job['channel'], job['rj_title'] = v.get('Job_Name').split('.', 1)

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
        self._get_job_info_all()

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

    def _create_jobscript(self, ch, title, begin, rectime, repeat=''):
        """
        ジョブスクリプトファイルを作成し、ファイル名を返す
        """
        command = self.recpt1[:]
        if self._is_bs(ch):
            command.append('--lnb 15')
            tuner = 'bs'
        else:
            tuner = 'tt'
        at = begin.strftime('%Y%m%d%H%M.%S')
        scriptname = '{}/{}.{}.{}.sh'.format(
                self.scriptdir,
                title,
                at,
                str(datetime.now().timestamp()),
                )
        try:
            with open(scriptname, 'w') as f:
                output = self.recdir + '/{}.{}'.format(title, ch)
                f.write(
                    dedent('''\
                        #PBS -N {_ch}.{_title}
                        #PBS -a {_at}
                        #PBS -l walltime={_walltime}
                        #PBS -l {_tuner}=1
                        #PBS -j oe
                        #PBS -o {_logdir}
                        #PBS -e {_logdir}
                        umask 022
                        _jobid=`echo $PBS_JOBID | awk -F'.' '{{printf("%05d", $1)}}'`
                        {_command} {_ch} - {_recdir}/{_title}.{_ch}.`date +%Y%m%d_%H%M.%S`.${{_jobid}}.ts
                    ''').format(
                        _ch=ch,
                        _title=title,
                        _at=at,
                        _walltime=str(int(rectime.total_seconds())),
                        _tuner=tuner,
                        _logdir=self.logdir,
                        _recdir=self.recdir,
                        _command=' '.join(command),
                    )
                )
        except (PermissionError, FileNotFoundError) as err:
            print('cannot create jobscript: {}'.format(err))
            sys.exit(1)

        return scriptname

    def _run_command(self, command):
        """
        コマンドを実行し、CompletedProcessオブジェクトを返す
        """
        try:
            proc = run(
                command,
                stdout=PIPE,
                stderr=PIPE,
                universal_newlines=True,
                timeout=self.comm_timeout,
                check=True,)
        except (TimeoutExpired, CalledProcessError) as err:
            print('{} failed: {}'.format(command[0], err))
            sys.exit(1)
        return proc

    def add(self, ch, title, begin, rectime, repeat=''):
        """
        下記の引数にて作成したジョブスクリプトをサブミットする
        ch:      チャンネル番号(str)
        title:   番組名(str)
        begin:   開始時間(datetime)
        rectime: 録画時間(timedelta)
        repeat:  繰り返しフラグ(str)

        qsubコマンドの標準出力の文字列からジョブIDを切り出して返す
        """
        scriptname = self._create_jobscript(ch, title, begin, rectime, repeat)

        qsub = self.qsub[:]
        qsub.append(scriptname)
        proc = self._run_command(qsub)
        jid = proc.stdout.split('.', 1)[0]

        return jid

    def _get_tuner_num(self):
        """
        利用可能なノードのカスタムリソース'tt'、'bs'を集計する
        """
        available = re.compile(r'free|job-busy')
        proc = self._run_command(self.pbsnodes)
        nodes = json.loads(proc.stdout).get('nodes', {})
        for v in nodes.values():
            if available.match(v.get('state', '')):
                resources = v.get('resources_available', {})
                self.tuners['tt'] += int(resources.get('tt', 0))
                self.tuners['bs'] += int(resources.get('bs', 0))

    def _check_tuner_resource(self):
        """
        チューナーの空き具合をチェックする
        最大同時録画数を超過しているジョブには警告をつける
        """
        message = 'Not enough tuners'
        self._get_tuner_num()
        counter = {'tt': [], 'bs': []}

        for job in self.joblist:
            _type = job.get('tuner')
            if len(counter.get(_type)) < self.tuners.get(_type):
                # チューナーに空きがある
                counter.get(_type).append(job)
            else:
                # ガベージコレクト
                for counted in counter.get(_type):
                    # counter内のジョブから録画終了しているものを削除
                    if job.get('rec_begin') > counted.get('rec_end'):
                        counter.get(_type).remove(counted)
                # 改めてチューナーの空きを確認
                if len(counter.get(_type)) < self.tuners.get(_type):
                    # 空きがある
                    counter.get(_type).append(job)
                else:
                    # 警告を追加
                    job['alert'] = message
                    for counted in counter.get(_type):
                        # 現時点でcounterに積まれているジョブにも警告を追加
                        counted['alert'] = message
