import requests, json
import os

class SlackBot(object):
    """docstring for SlackBot"""
    def __init__(self):
        super(SlackBot, self).__init__()
        self.base_url = "http://slack.com/api/"
        self.token = os.environ.get('SLACK_TOKEN') or "xoxp-36029697218-41442440934-217209477761-2cd3b8833197864fb746c7bbbb3599d9"
        self.username = 'Clubhouse'
        self.icon_url = 'http://www.qtozero.com/static/images/logo.png'

    def postMessage(self,channel, message):
        url = self.base_url + 'chat.postMessage'
        payload = {'token': self.token,
                   'channel': channel,
                   'text': message,
                   'username': self.username,
                   'icon_url': self.icon_url,
                   }

        r = requests.get(url, params=payload)
        data = json.loads(r.content)
        with open('BotLog.txt', 'w') as f:
            f.write(url + '\n\n')
            json.dump(payload, f)
            f.write('\n\n')
            json.dump(data, f)
            f.write('\n\n')
            f.write(r.url)

        # So, should really be doing error checking here,
        # but I'm skipping it for now.

