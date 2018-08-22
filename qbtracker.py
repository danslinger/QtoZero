import requests
import json
from app.models import Player, Owner
from app import db, create_app
import os, sys
from SlackBot import SlackBot
from datetime import datetime, date

def mysplit(s, delim=None):
    return [x for x in s.split(delim) if x]

# week = 3
league_id = 31348
url = 'http://www55.myfantasyleague.com/2017/export'
channel = 'QB_Tracker'


def getStartingLineups(url, league_id, week):
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
    r = requests.get(url,params=payload)
    data = r.json()['weeklyResults']

    teams = {f['id']: mysplit(f['starters'],',') for m in data['matchup'] for f in m['franchise']}
    return teams

def qbCount(players):
    return sum(1 for x in players if Player.query.filter_by(mfl_id=x).first().position == 'QB')

def reportToDateUsage(bot):
    message = ""
    allTeams = Owner.query.all()
    for team in allTeams:
        remaining = 6 - team.two_qbs
        message += "{0} has used two QB's {1} {2} this season. \n" \
                   .format(team.team_name, team.two_qbs, "time" if team.two_qbs == 1 else "times")
        message += "{0} can use two QB's {1} more {2}.\n\n" \
                   .format(team.team_name, remaining, "time" if remaining == 1 else "times")
    bot.post_message(channel, message)

def getWeekNumber(today=None):
    '''
    This week number is based on the 2017 NFL season.  In the future it'd be nice if you
    made it so it was season agnostic, but I'm not sure how to do that.  Maybe via
    an http request somewhere?  Anyway, this is probably overly complicated...
    '''
    if not today:
        today = date.today()
    weeks = {'1': [date(2017,9,5), date(2017,9,11)],
             '2': [date(2017,9,12), date(2017,9,18)],
             '3': [date(2017,9,19), date(2017,9,25)],
             '4': [date(2017,9,26), date(2017,10,2)],
             '5': [date(2017,10,3), date(2017,10,9)],
             '6': [date(2017,10,10), date(2017,10,16)],
             '7': [date(2017,10,17), date(2017,10,23)],
             '8': [date(2017,10,24), date(2017,10,30)],
             '9': [date(2017,10,31), date(2017,11,6)],
             '10': [date(2017,11,7), date(2017,11,13)],
             '11': [date(2017,11,14), date(2017,11,20)],
             '12': [date(2017,11,21), date(2017,11,27)],
             '13': [date(2017,11,28), date(2017,12,4)],
             '14': [date(2017,12,5), date(2017,12,11)],
             '15': [date(2017,12,12), date(2017,12,18)],
             '16': [date(2017,12,19), date(2017,12,25)],
             '17': [date(2017,12,26), date(2018,1,1)],
            }
    for weekNumber, weekDates in weeks.iteritems():
        if weekDates[1] > today >= weekDates[0]:
            return weekNumber
    return 0 


if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_CONFIG') or 'default').app_context().push()
    if len(sys.argv) > 1:
        week = sys.argv[1]
    else:
        week = int(getWeekNumber()) - 1  #getWeekNumber gets current week.  We want last weeks 
    startingLineups = getStartingLineups(url, league_id, week)
    message = "QB Tracker for Week " + week + "\n\n"
    for team_id, players in startingLineups.iteritems():
        numberQBPlayed = qbCount(players)
        team = Owner.query.filter_by(mfl_team_id=team_id).first()
        if numberQBPlayed > 1:
            message += "{0} started 2 QBs this week.\n".format(team.team_name)
            team.two_qbs = team.two_qbs + 1

    db.session.commit()

    bot = SlackBot()
    bot.post_message(channel, message)

    reportToDateUsage(bot)
