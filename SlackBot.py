import requests, json
import os

class SlackBot(object):
    """docstring for SlackBot"""
    def __init__(self):
        super(SlackBot, self).__init__()
        self.base_url = "https://slack.com/api"
        self.token = os.environ.get('SLACK_TOKEN')
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
        print url, payload
        r = requests.post(url, params=payload)
        data = json.loads(r.content)
        # So, should really be doing error checking here,
        # but I'm skipping it for now.

