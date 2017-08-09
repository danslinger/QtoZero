from crontab import CronTab
import datetime


class TaskScheduler(object):
    """docstring for TaskScheduler"""
    def __init__(self):
        super(TaskScheduler, self).__init__()
        self.cron = CronTab(user=True)

    def getJob(self, comment):
        jobs = [job for job in self.cron.find_comment(comment)]
        if jobs:
            return jobs[0]
        else:
            return None

    def setJob(self, job, date):
        job.setall(date)
        self.cron.write()

