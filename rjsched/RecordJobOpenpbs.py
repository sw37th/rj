from datetime import datetime, timedelta
from subprocess import run, PIPE, STDOUT, DEVNULL, CalledProcessError
import hashlib
import os
import sys

class RecordJobOpenpbs:
    def __init__(self):
        pbsexec = '/work/pbs/bin/'
        self.qstat = [pbsexec + 'qstat', '-f', '-1']
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
