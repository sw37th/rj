from datetime import datetime, timedelta
from subprocess import run, PIPE, STDOUT, DEVNULL, CalledProcessError, TimeoutExpired
import hashlib
import json
import os
import sys

class RecordJobOpenpbs:
    def __init__(self):
        pbsexec = '/work/pbs/bin/'
        self.qstat = [pbsexec + 'qstat', '-f', '-F', 'json']
        self.pbsnodes = [pbsexec + 'pbsnodes', '-a']
        self.qsub = [pbsexec + 'qsub']
        self.qalter = [pbsexec + 'qalter', '-a' ]
        self.comm_timeout = 10
        self.recpt1_path = '/usr/local/bin/recpt1'
        self.scriptdir = '/home/autumn/jobsh'
        self.logdir = '/home/autumn/log'
        self.recdir = '/home/autumn/rec'
        self.channel_file = '/home/autumn/work/rj/channel.yml'
        self.job_state = {
            'C': "Completed",
            'E': "Exiting",
            'H': "on Hold",
            'Q': "Queued",
            'R': "Recording",
            'T': "Moved",
            'W': "Waiting",
            'S': "Suspend",
        }
        self.queuename = {
            'satellite': 'bs',
            'terrestrial': 'tt',
        }

    def _qstat(self):
        try:
            ret = run(
                self.qstat,
                timeout=self.comm_timeout,
                check=True,
                stdout=PIPE,
                stderr=STDOUT,
            )
            jobs = json.loads(ret.stdout)
            print(jobs)

        except (CalledProcessError, TimeoutExpired) as err:
            print('cannot get job information: {}'.format(err))
