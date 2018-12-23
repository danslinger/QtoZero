import os
import sys
from datetime import date

import requests

from SlackBot import SlackBot
from app import db, create_app
from app.models import Player, Owner


def my_split(s, delim=None):
    return [x for x in s.split(delim) if x]


# week = 3
league_id = 31348
year = 2018
url = f'http://www55.myfantasyleague.com/{year}/export'
channel = 'QB_Tracker'


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

    teams = {f['id']: my_split(f['starters'], ',') for m in data['matchup'] for f in m['franchise']}
    return teams


def qb_count(_players):
    return sum(1 for x in _players if Player.query.filter_by(mfl_id=x).first().position == 'QB')


def report_to_date_usage(bot):
    msg = ""
    all_teams = Owner.query.all()
    for t in all_teams:
        remaining = 6 - t.two_qbs
        msg += f'{t.team_name}: {remaining}/6 remaining\n\n'

    bot.post_message(channel, message)


def get_week_number(today=None):
    '''
    This week number is based on the 2017 NFL season.  In the future it'd be nice if you
    made it so it was season agnostic, but I'm not sure how to do that.  Maybe via
    an http request somewhere?  Anyway, this is probably overly complicated...
    '''
    if not today:
        today = date.today()
    weeks = {'1': [date(2018, 9, 4), date(2018, 9, 10)],
             '2': [date(2018, 9, 11), date(2018, 9, 17)],
             '3': [date(2018, 9, 18), date(2018, 9, 24)],
             '4': [date(2018, 9, 25), date(2018, 10, 1)],
             '5': [date(2018, 10, 2), date(2018, 10, 8)],
             '6': [date(2018, 10, 9), date(2018, 10, 15)],
             '7': [date(2018, 10, 16), date(2018, 10, 22)],
             '8': [date(2018, 10, 23), date(2018, 10, 29)],
             '9': [date(2018, 10, 30), date(2018, 11, 5)],
             '10': [date(2018, 11, 6), date(2018, 11, 12)],
             '11': [date(2018, 11, 13), date(2018, 11, 19)],
             '12': [date(2018, 11, 20), date(2018, 11, 26)],
             '13': [date(2018, 11, 27), date(2018, 12, 3)],
             '14': [date(2018, 12, 4), date(2018, 12, 10)],
             '15': [date(2018, 12, 11), date(2018, 12, 17)],
             '16': [date(2018, 12, 18), date(2018, 12, 24)],
             '17': [date(2018, 12, 25), date(2018, 12, 31)],
             }
    for weekNumber, weekDates in weeks.items():
        if weekDates[1] >= today >= weekDates[0]:
            return weekNumber
    return 0


if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_CONFIG') or 'default').app_context().push()
    if len(sys.argv) > 1:
        week = sys.argv[1]
    else:
        week = int(get_week_number()) - 1  # getWeekNumber gets current week.  We want last weeks
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
    # bot.post_message(channel, message)

    report_to_date_usage(bot)
