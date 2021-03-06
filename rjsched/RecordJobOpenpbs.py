from copy import deepcopy
from datetime import datetime, timedelta
from textwrap import dedent
import json
import os
import re
import rjsched
import sys

class RecordJobOpenpbs(rjsched.RecordJob):
    def __init__(self, config):
        super().__init__(config)
        self.name = 'RecordJobOpenpbs'
        pbsexec = config.get('pbsexec_dir')
        self.logdir = config.get('joblog_dir')
        self.qstat = [pbsexec + '/qstat', '-f', '-F', 'json']
        self.pbsnodes = [pbsexec + '/pbsnodes', '-a', '-F', 'json']
        self.qsub = [pbsexec + '/qsub']
        self.qdel = [pbsexec + '/qdel']
        self.qalter = [pbsexec + '/qalter']
        self.joblist = []

    def __str__(self):
        return self.name

    def _get_tuner_num(self):
        """
        利用可能なノードのカスタムリソース'tt'、'bs'を集計する
        """
        tuners = {'tt': 0, 'bs': 0}

        available = re.compile(r'free|job-busy')
        proc = self._run_command(self.pbsnodes, log=False)
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
            if _type == 'not_rec_job':
                continue
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
        'elapse':       録画開始からの経過時間 (timedelta)
        'qtime':        ジョブのキュー追加時刻 (datetime)
        'ctime':        ジョブの作成時刻 (datetime)
        'mtime':        ジョブをMoMが最後にモニタした時刻 (datetime)
        'alert':        警告メッセージ (str)
        """
        # 同一インスタンスで複数回呼ばれた際に古い情報を返さないよう毎回クリアする
        self.joblist.clear()
        current = datetime.now()
        chlist = self.get_channel_list()

        proc = self._run_command(self.qstat, log=False)
        jobs = json.loads(proc.stdout).get('Jobs', {})
        for k, v in jobs.items():
            # ジョブID、チャンネル番号、番組名
            job = {'rj_id': k.split('.')[0]}
            jobname = v.get('Job_Name').split('.', 1)
            if len(jobname) < 2:
                # ジョブ名が "番組名.チャンネル番号" 形式ではない
                job['rj_title'] = jobname[0]
                job['channel'] = '0'
            else:
                job['rj_title'] = jobname[0]
                if jobname[1].isdigit():
                    job['channel'] = jobname[1]
                else:
                    # 不正なチャンネル番号
                    job['channel'] = '0'
            job['station_name'] = chlist.get(job.get('channel'), '')

            # 録画時間
            wt_h, wt_m, wt_s = [
                int(i) for i in v.get('Resource_List').get('walltime').split(':')]
            job['walltime'] = timedelta(hours=wt_h, minutes=wt_m, seconds=wt_s)

            # ジョブの状態、録画開始時刻、録画終了時間、録画開始からの経過時間
            state = v.get('job_state')
            if state == "W":
                # waiting
                job['rec_begin'] = datetime.strptime(
                    v.get('Execution_Time'), "%a %b %d %H:%M:%S %Y")
                job['elapse'] = None
            else:
                # queued or running
                job['rec_begin'] = datetime.strptime(
                    v.get('etime'), "%a %b %d %H:%M:%S %Y")
                job['elapse'] = current - job['rec_begin']
                job['exec_host'] = v.get('exec_host', 'dummy/dummy').split('/')[0]
            job['rec_end'] = job['rec_begin'] + job['walltime']
            job['record_state'] = self.job_state.get(state)

            # 地上波(tt) or 衛星放送(bs)
            tuner = [k for k in v.get('Resource_List').keys()
                if k == 'tt' or k == 'bs']
            if tuner:
                job['tuner'] = tuner[0]
            else:
                # 録画ジョブ以外のジョブの場合
                job['tuner'] = 'not_rec_job'

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
            self.joblist, key=lambda x: x['rec_begin'])

    def get_job_list(self, jid=''):
        """
        ジョブ情報をリストに詰め、呼び出し元に返す
        下記の引数が指定されている場合はそのジョブ情報のみ抽出する

        jid:  ジョブID (str)
        """

        # ジョブ情報リスト取得
        self._fetch_joblist()

        # 最大同時録画数のチェック
        self._check_tuner_resource()

        if jid:
            # 指定されたジョブIDの情報のみ抽出
            joblist = [i for i in self.joblist if i['rj_id'] in jid]
        else:
            # 全ジョブ
            joblist = self.joblist

        return deepcopy(joblist)

    def add(self, ch, title, begin, rectime, repeat=''):
        """
        ジョブをサブミットし、ジョブ情報リストを返す

        ch:      チャンネル番号(str)
        title:   番組名(str)
        begin:   開始時間(datetime)
        rectime: 録画時間(timedelta)
        repeat:  繰り返しフラグ(str)
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
                '-l', 'walltime={}'.format(rectime.total_seconds()),
                '-l', '{}=1'.format(tuner),
                '-j', 'oe',
                '-o', self.logdir,
                '-W', 'umask=222',
                '-',]

        proc = self._run_command(command=qsub, _input=jobexec)
        return self.get_job_list(proc.stdout.split('.', 1)[0])

    def remove(self, jid=''):
        """
        引数で与えられたIDのジョブを削除する
        FIXME: 引数をstrではなくlistに変更して複数ジョブを一括削除

        削除したジョブ情報のリストを返す
        """
        joblist = self.get_job_list(jid)
        if joblist:
            qdel = self.qdel[:]
            qdel.append(jid)
            self._run_command(qdel)

        return joblist

    def change_begin(self, joblist, begin=None, delta=None):
        """
        録画ジョブの開始時刻を指定時刻に変更
        変更後のジョブ情報を格納したjoblistを返す

        joblist: 変更対象ジョブの格納されたjoblist (list)
                 複数のジョブ情報が格納されている場合は先頭のみ使用
        begin:   録画開始時刻 (datetime)
                 begin, deltaが両方指定された場合はdeltaが優先される
        delta:   現在の録画開始時刻との差分 (timedelta)
                 begin, deltaが両方指定された場合はdeltaが優先される
        """
        jid = joblist[0].get('rj_id')
        if delta:
            begin = joblist[0].get('rec_begin') + delta
        qalter = self.qalter[:]
        qalter.extend(['-a', begin.strftime('%Y%m%d%H%M.%S'), jid])
        self._run_command(qalter)

        return self.get_job_list(jid)

    def change_rectime(self, joblist, rectime=None, delta=None):
        """
        録画時間を指定時間に変更
        変更後のジョブ情報を格納したjoblistを返す

        joblist: 変更対象ジョブの格納されたjoblist (list)
                 複数のジョブ情報が格納されている場合は先頭のみ使用
        rectime: 録画時間 (timedelta)
                 rectime, deltaが両方指定された場合はdeltaを優先する
        delta:   現在の録画時間との差分 (timedelta)
                 rectime, deltaが両方指定された場合はdeltaを優先する
        """
        jid = joblist[0].get('rj_id')
        if delta:
            rectime = joblist[0].get('walltime') + delta
        qalter = self.qalter[:]
        qalter.extend([
            '-l', 'walltime={}'.format(rectime.total_seconds()), jid])
        self._run_command(qalter)

        return self.get_job_list(jid)

    def _change_jobname(self, joblist, name='', ch=''):
        """
        "番組名"."チャンネル番号" で構成されるOpenPBSジョブ名を変更する
        変更後のジョブ情報を格納したjoblistを返す

        joblist:  ジョブリスト (list)
        name:     新しい番組名 (str)
        ch:       新しいチャンネル番号 (str)

        FIXME:
        現在は待機中のジョブのみ対応。
        録画中ジョブ('record_state': 'Running')の場合はqalterに加えて下記も行う。
            番組名変更:     mvで録画ファイル名を変更
            チャンネル変更: mvで録画ファイル名を変更
                            + recpt1ctlでチューナーのチャンネルを変更
        """
        jid = joblist[0].get('rj_id')
        if not name:
            name = joblist[0].get('rj_title')
        if not ch:
            ch = joblist[0].get('channel')

        qalter = self.qalter[:]
        qalter.extend([
            '-N', '{}.{}'.format(name, ch), jid])
        self._run_command(qalter)

        return self.get_job_list(jid)

    def change_channel(self, joblist, ch):
        """
        _change_jobname()のラッパー
        録画するチャンネルを変更する
        変更後のジョブ情報を格納したjoblistを返す

        joblist: ジョブリスト (list)
        ch:      新しいチャンネル番号 (str)
        """
        return self._change_jobname(joblist=joblist, ch=ch)

    def change_name(self, joblist, name):
        """
        _change_jobname()のラッパー
        番組名を変更する
        変更後のジョブ情報を格納したjoblistを返す

        joblist: ジョブリスト (list)
        name:    新しい番組名 (str)
        """
        return self._change_jobname(joblist=joblist, name=name)
