import requests
import json
from tokens import tokens
from app import create_app
from app.models.player import Player
from app.models.owner import Owner
from app.models.pro_bowl_roster import ProbowlRoster
from constants import LEAGUE_ID, YEAR, MFL_URL
import csv

league_id = LEAGUE_ID
year = YEAR
url = MFL_URL
api_token = tokens['mfl_token']


def get_Score(player):
    payload = {'TYPE': 'playerScores',
               'JSON': 1,
               'YEAR': year,
               'L': league_id,
               'PLAYERS': Player.query.get(player).mfl_id
               }
    r = requests.get(url, params=payload)
    data = json.loads(r.content)
    return data['playerScores']['playerScore'][-1]['score']


def get_scores(roster):
    scores = {}
    scores['qb'] = (roster.qb, get_Score(roster.qb))
    scores['rb1'] = (roster.rb1, get_Score(roster.rb1))
    scores['rb2'] = (roster.rb2, get_Score(roster.rb2))
    scores['wr1'] = (roster.wr1, get_Score(roster.wr1))
    scores['wr2'] = (roster.wr2, get_Score(roster.wr2))
    scores['wr3'] = (roster.wr3, get_Score(roster.wr3))
    scores['te'] = (roster.te, get_Score(roster.te))
    scores['pk'] = (roster.pk, get_Score(roster.pk))
    scores['dst'] = (roster.dst, get_Score(roster.dst))
    scores['flex'] = (roster.flex, get_Score(roster.flex))
    return scores


if __name__ == '__main__':
    create_app('probowl').app_context().push()
    rosters = ProbowlRoster.query.all()
    scores = {}
    for roster in rosters:
        scores[roster.owner_id] = get_scores(roster)
    with open('probowl.csv', 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile, dialect='excel')
        team_names = []
        for i in list(scores.keys()):
            team_names.append(Owner.query.get(i).team_name)
            team_names.append(',')
        header = [''] + team_names
        csv_writer.writerow(header)
        rows = {'QB': ['QB'], 'RB1': ['RB1'],
                'RB2': ['RB2'], 'WR1': ['WR1'],
                'WR2': ['WR2'], 'WR3': ['WR3'],
                'TE': ['TE'], 'K': ['K'],
                'DST': ['DST'], 'FLEX': ['FLEX'],
                }
        for k, v in scores.items():
            rows['QB'] += [Player.query.get(v['qb'][0]).name, v['qb'][1]]
            rows['RB1'] += [Player.query.get(v['rb1'][0]).name, v['rb1'][1]]
            rows['RB2'] += [Player.query.get(v['rb2'][0]).name, v['rb2'][1]]
            rows['WR1'] += [Player.query.get(v['wr1'][0]).name, v['wr1'][1]]
            rows['WR2'] += [Player.query.get(v['wr2'][0]).name, v['wr2'][1]]
            rows['WR3'] += [Player.query.get(v['wr3'][0]).name, v['wr3'][1]]
            rows['TE'] += [Player.query.get(v['te'][0]).name, v['te'][1]]
            rows['DST'] += [Player.query.get(v['dst'][0]).name, v['dst'][1]]
            rows['K'] += [Player.query.get(v['pk'][0]).name, v['pk'][1]]
            rows['FLEX'] += [Player.query.get(v['flex'][0]).name, v['flex'][1]]
        csv_writer.writerow(rows['QB'])
        csv_writer.writerow(rows['RB1'])
        csv_writer.writerow(rows['RB2'])
        csv_writer.writerow(rows['WR1'])
        csv_writer.writerow(rows['WR2'])
        csv_writer.writerow(rows['WR3'])
        csv_writer.writerow(rows['TE'])
        csv_writer.writerow(rows['K'])
        csv_writer.writerow(rows['DST'])
        csv_writer.writerow(rows['FLEX'])
