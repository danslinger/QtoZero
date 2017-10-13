import requests, json
import os
import tokens

class SlackBot(object):
    """docstring for SlackBot"""
    def __init__(self):
        super(SlackBot, self).__init__()
        self.base_url = "http://slack.com/api/"
        self.username = 'Clubhouse'
        self.icon_url = 'http://www.qtozero.com/static/images/logo.png'
        self.getSlackToken()

    def getSlackToken(self):
        # with open('.app_tokens') as f:
        #     data = json.load(f)
        self.token = tokens.tokens['slack_token']

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
        with open('/home/danny/BotLog.txt', 'w') as f:
            f.write(url + '\n\n')
            json.dump(payload, f)
            f.write('\n\n')
            json.dump(data, f)
            f.write('\n\n')
            f.write(r.url)

        # So, should really be doing error checking here,
        # but I'm skipping it for now.

