import json
import requests
from tokens import tokens
from .. import db

league_id = 31348
year = 2019
url = f'http://www55.myfantasyleague.com/{year}/export'
api_token = tokens['mfl_token']


class Player(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    team = db.Column(db.String(16))
    mfl_id = db.Column(db.String(16))
    position = db.Column(db.String(8))
    nfl_id = db.Column(db.String(32))
    rotoworld_id = db.Column(db.String(32))
    stats_id = db.Column(db.String(32))
    espn_id = db.Column(db.String(32))
    kffl_id = db.Column(db.String(32))
    sportsdata_id = db.Column(db.String(32))
    cbs_id = db.Column(db.String(32))
    twitter_username = db.Column(db.String(32))
    mfl_team = db.Column(db.Integer, db.ForeignKey('owners.id'))
    previous_owner_id = db.Column(db.Integer)
    salary = db.Column(db.Integer)
    contractStatus = db.Column(db.String(8))
    status = db.Column(db.String(16))  # ROSTER, TAXI_SQUAD, INJURED_RESERVE
    contractYear = db.Column(db.String(16))
    tag = db.Column(db.String(8))  # [TRANS, FRAN, SUPER_FRAN]
    upForBid = db.Column(db.Boolean, default=False)
    finishedBidding = db.Column(db.Boolean, default=False)

    def to_dict(self):
        d = {
            'id': self.id,
            'name': self.name,
            'position': self.position
        }
        return d

    def __init__(self, mfl_dict):
        self.update_player(mfl_dict)

    def update_player(self, mfl_dict):
        self.name = self.name_swap(mfl_dict.get('name'))  # Expects last,first
        self.team = mfl_dict.get('team')
        self.mfl_id = mfl_dict.get('id')
        self.position = mfl_dict.get('position')
        self.nfl_id = mfl_dict.get('nfl_id')
        self.rotoworld_id = mfl_dict.get('rotoworld_id')
        self.stats_id = mfl_dict.get('stats_id')
        self.espn_id = mfl_dict.get('espn_id')
        self.kffl_id = mfl_dict.get('kffl_id')
        self.sportsdata_id = mfl_dict.get('sportsdata_id')
        self.cbs_id = mfl_dict.get('cbs_id')
        self.twitter_username = mfl_dict.get('twitter_username')

    def update_contract_info(self, contract_info):
        self.contractYear = contract_info.get('contractYear')
        self.contractStatus = contract_info.get('contractStatus')
        self.status = contract_info.get('status') or "FA"
        self.salary = contract_info.get('salary')

    def reset_contract_info(self, current_owner_id):
        payload = {'TYPE': 'rosters',
                   'JSON': 1,
                   'L': league_id,
                   'FRANCHISE': current_owner_id,
                   'APIKEY': api_token,
                   }
        r = requests.get(url, params=payload)
        roster = json.loads(r.content)
        for data in roster['rosters']['franchise']['player']:
            if data.get('id') == self.mfl_id:
                self.update_contract_info(data)
                self.tag = None
                break

    def update_roster_info(self, contract_info, mfl_id):
        """
        contract_info contains a dictionary in the form:
        {
            "contractYear": "2" #Josh changed this to the total years of the contract, which messed me up and is stupid
            "contractStatus": "K", # or T or F or S
            "status": "ROSTER",
            "id": "11175",
            "salary": "15"
            "contract_info": 1 # represents the years remaining on the contract
        }
        mfl_id is the mfl_id of the owner.  Need to take this value and find
        the owner.id and assign that to the Player.mfl_team (the foreign key is to owner.id)

        **maybe change mfl_team to owner NOPE, because of the backref owner**
        """
        self.contractYear = contract_info.get('contractInfo')
        self.contractStatus = contract_info.get('contractStatus')
        # all should have this.  Not sure why I added or "FA"
        self.status = contract_info.get('status') or "FA"
        self.salary = contract_info.get('salary')
        self.mfl_team = self.set_mfl_team_from_mfl_id(mfl_id)
        # if self.contractStatus == "K":
        #     print(self.name, contract_info.get('contractInfo'), contract_info.get('contractStatus'))

    def update_owner(self, new_owner_id):
        self.previous_owner_id = self.mfl_team
        self.mfl_team = new_owner_id

    # @staticmethod
    # def set_mfl_team_from_mfl_id(mfl_id):
    #     # FIXME This is only used in player_setup.py
        # This should be re-worked
    #     return
    #     # return Owner.query.filter_by(mfl_team_id=mfl_id).first().id

    @staticmethod
    def name_swap(name_str):
        tmp = name_str.split(', ')
        tmp.reverse()
        return " ".join(tmp)

    def __repr__(self):
        return '<Player id:{0}; name:{1}; mfl_id:{2}>'.format(self.id, self.name, self.mfl_id)
