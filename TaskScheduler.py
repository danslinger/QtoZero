from crontab import CronTab


class TaskScheduler(object):
    """docstring for TaskScheduler"""

    def __init__(self):
        super(TaskScheduler, self).__init__()
        try:
            self.cron = CronTab(user="danny")
        except:
            self.cron = None

    def get_job(self, comment, command=''):
        if self.cron is None:
            return
        jobs = [job for job in self.cron.find_comment(comment)]
        if jobs:
            return jobs[0]
        else:
            return self.cron.new(command=command, comment=comment)

    def set_job(self, job, date):
        if self.cron is None:
            return
        job.setall(date)
        self.cron.write()
