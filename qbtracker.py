import os
import sys
from datetime import date

import requests

from SlackBot import SlackBot
from app import db, create_app
from app.models.player import Player
from app.models.owner import Owner
from constants import LEAGUE_ID, YEAR, MFL_URL


def my_split(s, delim=None):
    return [x for x in s.split(delim) if x]


# week = 3
league_id = LEAGUE_ID
year = YEAR
url = MFL_URL
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

    bot.post_message(msg, channel)


def get_week_number(today=None):
    '''
    This week number is based on the 2019 NFL season.  In the future it'd be nice if you
    made it so it was season agnostic, but I'm not sure how to do that.  Maybe via
    an http request somewhere?  Anyway, this is probably overly complicated...
    '''
    nfl_week0 = date(2020, 9, 6)  # Sunday before first game

    if not today:
        today = date.today()

    this_week = today.isocalendar()[1]
    if today.year > year and this_week < 53:
        this_week += 53

    return this_week - nfl_week0.isocalendar()[1]


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
