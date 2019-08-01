from crontab import CronTab


class TaskScheduler(object):
    """docstring for TaskScheduler"""
    def __init__(self):
        super(TaskScheduler, self).__init__()
        self.cron = CronTab(user="danny")

    def get_job(self, comment, command=''):
        jobs = [job for job in self.cron.find_comment(comment)]
        if jobs:
            return jobs[0]
        else:
            return self.cron.new(command=command, comment=comment)

    def set_job(self, job, date):
        job.setall(date)
        self.cron.write()
