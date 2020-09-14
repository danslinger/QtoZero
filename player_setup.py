import os
import json
import requests
from app.models.player import Player
from app.models.owner import Owner
from app import db, create_app
from tokens import tokens
from constants import LEAGUE_ID, MFL_URL, POSITIONS

api_token = tokens['mfl_token']


def get_all_players():
    ''' Gets all the players from MFL that are positions our league uses'''
    payload = {'TYPE': 'players',
               'JSON': 1,
               'DETAILS': 1,
               'L': LEAGUE_ID,
               'APIKEY': api_token
               }
    r = requests.get(MFL_URL, params=payload)
    data = json.loads(r.content)
    mfl_players = data['players']['player']
    calvinball_players = [
        player for player in mfl_players if player['position'] in POSITIONS]
    return calvinball_players


def get_all_rosters():
    """
    Gets all the rosters
    rosters is returned as a list of franchises.  Each franchise then
    has an id and a list of players.  Each player has a dictionary of
    contractYear, contractStatus, status, id, and salary.
    """
    payload = {'TYPE': 'rosters',
               'JSON': 1,
               'L': LEAGUE_ID,
               'APIKEY': api_token
               }
    r = requests.get(MFL_URL, params=payload)
    data = r.json()
    rosters = data['rosters']

    return rosters


def main():
    # noinspection PyUnusedLocal
    create_app(os.getenv('FLASK_CONFIG')
               or 'default').app_context().push()
    calvinball_players = get_all_players()
    rosters = get_all_rosters()

    players = []
    for x in calvinball_players:
        player_object = Player.query.filter_by(mfl_id=x.get('id')).first()
        if player_object:
            player_object.owner = None
            player_object.update_player(x)
            players.append(player_object)
        else:
            players.append(Player(x))

    for franchise in rosters['franchise']:
        for fp in franchise['player']:
            p = next((x for x in players if x.mfl_id == fp.get('id')))
            # p should be a Player object.  Update p now

            p.update_roster_info(fp)
            p.owner = Owner.query.filter_by(
                mfl_team_id=franchise.get('id')).first()
    db.session.add_all(players)
    db.session.commit()


if __name__ == '__main__':
    main()
