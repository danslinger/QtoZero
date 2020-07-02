import os
import sys
from datetime import date

import requests

from SlackBot import SlackBot
from app import db, create_app
from app.models.player import Player
from app.models.owner import Owner


def my_split(s, delim=None):
    return [x for x in s.split(delim) if x]


# week = 3
league_id = 31348
year = 2019
url = f'http://www55.myfantasyleague.com/{year}/export'
channel = 'qb_tracker_url'


def get_starting_lineups(url, league_id, week):
    '''
        Returns a dictionary of team ids and their starting lineups.  Example:  
        {
            "0004":[
                    "9817",
                    "10273",
                    "9680",
                    "12912",
                    "11213",
                    "9436",
                    "9525",
                    "10743",
                    "11945",
                    "0528"
            ], ...
        }
    '''

    payload = {'L': league_id, 'JSON': 1, 'W': week, 'TYPE': 'weeklyResults'}
    r = requests.get(url, params=payload)
    data = r.json()['weeklyResults']

    teams = {f['id']: my_split(f['starters'], ',')
             for m in data['matchup'] for f in m['franchise']}
    return teams


def qb_count(_players):
    return sum(1 for x in _players if Player.query.filter_by(mfl_id=x).first().position == 'QB')


def report_to_date_usage(bot):
    msg = ""
    all_teams = Owner.query.all()
    for t in all_teams:
        remaining = 6 - t.two_qbs
        msg += f'{t.team_name}: {remaining}/6 remaining\n\n'

    bot.post_message msg, channel)


def get_week_number(today=None):
    '''
    This week number is based on the 2019 NFL season.  In the future it'd be nice if you
    made it so it was season agnostic, but I'm not sure how to do that.  Maybe via
    an http request somewhere?  Anyway, this is probably overly complicated...
    '''
    if not today:
        today = date.today()
    weeks = {'1': [date(2019, 9, 3), date(2019, 9, 9)],
             '2': [date(2019, 9, 10), date(2019, 9, 16)],
             '3': [date(2019, 9, 17), date(2019, 9, 23)],
             '4': [date(2019, 9, 24), date(2019, 9, 30)],
             '5': [date(2019, 10, 1), date(2019, 10, 7)],
             '6': [date(2019, 10, 8), date(2019, 10, 14)],
             '7': [date(2019, 10, 15), date(2019, 10, 21)],
             '8': [date(2019, 10, 22), date(2019, 10, 28)],
             '9': [date(2019, 10, 29), date(2019, 11, 4)],
             '10': [date(2019, 11, 5), date(2019, 11, 11)],
             '11': [date(2019, 11, 12), date(2019, 11, 18)],
             '12': [date(2019, 11, 19), date(2019, 11, 25)],
             '13': [date(2019, 11, 26), date(2019, 12, 2)],
             '14': [date(2019, 12, 3), date(2019, 12, 9)],
             '15': [date(2019, 12, 10), date(2019, 12, 16)],
             '16': [date(2019, 12, 17), date(2019, 12, 23)],
             '17': [date(2019, 12, 24), date(2020, 1, 1)],
             }
    for weekNumber, weekDates in weeks.items():
        if weekDates[1] >= today >= weekDates[0]:
            return weekNumber
    return 0


if __name__ == '__main__':
    create_app(os.getenv('FLASK_CONFIG') or 'default').app_context().push()
    if len(sys.argv) > 1:
        week = sys.argv[1]
    else:
        # getWeekNumber gets current week.  We want last weeks
        week = int(get_week_number()) - 1
    startingLineups = get_starting_lineups(url, league_id, week)
    message = f'QB Tracker for Week {week} \n\n'
    for team_id, players in startingLineups.items():
        numberQBPlayed = qb_count(players)
        team = Owner.query.filter_by(mfl_team_id=team_id).first()
        if numberQBPlayed > 1:
            message += "{0} started 2 QBs this week.\n".format(team.team_name)
            team.two_qbs = team.two_qbs + 1

    db.session.commit()

    bot = SlackBot()
    bot.post_message(message, channel)

    report_to_date_usage(bot)
