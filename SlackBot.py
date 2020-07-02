import requests, json
from tokens import tokens


class SlackBot(object):
    """docstring for SlackBot"""
    def __init__(self):
        super(SlackBot, self).__init__()

    def post_message(self, message, channel_key):
        url = tokens[channel_key]
        payload = {
            'text': message,
        }

        r = requests.post(url, json=payload)
        if r.status_code != 200:
            with open('/home/danny/BotLog.txt', 'w') as f:
                f.write(url + '\n\n')
                f.write(r)

        # So, should really be doing error checking here,
        # but I'm skipping it for now.
