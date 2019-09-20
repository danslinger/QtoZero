import json
import requests
from flask_login import UserMixin
from sqlalchemy.sql.expression import and_
from tokens import tokens
from werkzeug.security import generate_password_hash, check_password_hash

from . import db, login_manager

league_id = 31348
year = 2019
url = f'http://www55.myfantasyleague.com/{year}/export'
api_token = tokens['mfl_token']


class Owner(UserMixin, db.Model):
    __tablename__ = 'owners'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    name = db.Column(db.String(64))
    team_name = db.Column(db.String(64))
    password_hash = db.Column(db.String(128))
    mfl_team_id = db.Column(db.String(16))
    phone = db.Column(db.String(16))
    twitter = db.Column(db.String(32))
    players = db.relationship('Player', backref='owner', lazy='dynamic')
    keeperSet = db.Column(db.Boolean, default=False)
    draftPicks = db.relationship('DraftPick', backref='owner', lazy='dynamic')
    madeBid = db.Column(db.Boolean, default=False)
    image_name = db.Column(db.String(128))
    two_qbs = db.Column(db.Integer, default=0)
    division_id = db.Column(db.Integer, db.ForeignKey('division.id'))

    @property
    def password(self):
        return AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def keepers(self):
        return self.players.filter(and_(Player.contractStatus == "K", Player.contractYear == "1")).count()
        # write a query to return the number of keepers on a roster

    def to_dict(self):
        d = {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'team_name': self.team_name,
            'mfl_team_id': self.mfl_team_id,
            'phone': self.phone,
            'twitter': self.twitter,
            'keeperCount': self.keepers(),
            'keeperSet': self.keeperSet,
            'madeBid': self.madeBid,
            'image_name': self.image_name,
            'division_id': self.division_id,
        }
        return d

    def has_pick(self, rd):
        picks = self.draftPicks.filter(DraftPick.draftRound == rd).all()
        if picks:
            return True
        else:
            return False

    def __repr__(self):
        return '<Owner %r>' % self.team_name


@login_manager.user_loader
def load_user(user_id):
    return Owner.query.get(int(user_id))


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
    twitter_username = db.column(db.String(32))
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
        self.status = contract_info.get('status') or "FA"  # all should have this.  Not sure why I added or "FA"
        self.salary = contract_info.get('salary')
        self.mfl_team = self.set_mfl_team_from_mfl_id(mfl_id)
        # if self.contractStatus == "K":
        #     print(self.name, contract_info.get('contractInfo'), contract_info.get('contractStatus'))

    def update_owner(self, new_owner_id):
        self.previous_owner_id = self.mfl_team
        self.mfl_team = new_owner_id

    @staticmethod
    def set_mfl_team_from_mfl_id(mfl_id):
        return Owner.query.filter_by(mfl_team_id=mfl_id).first().id

    @staticmethod
    def name_swap(name_str):
        tmp = name_str.split(', ')
        tmp.reverse()
        return " ".join(tmp)

    def __repr__(self):
        return '<Player id:{0}; name:{1}; mfl_id:{2}>'.format(self.id, self.name, self.mfl_id)


class DraftPick(db.Model):
    __tablename__ = "draftpicks"
    id = db.Column(db.Integer, primary_key=True)
    draftRound = db.Column(db.Integer)
    pickInRound = db.Column(db.Integer)
    owner_id = db.Column(db.Integer, db.ForeignKey('owners.id'))

    def update_pick(self, new_owner_id):
        self.owner_id = new_owner_id

    def __repr__(self):
        owner_name = Owner.query.get(self.owner_id)
        return '<Round:{0}; Pick:{1}; Owner:{2}>'.format(self.draftRound, self.pickInRound, owner_name)


class Bid(db.Model):
    __tablename__ = "bids"
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'))
    owner_bidding_id = db.Column(db.Integer, db.ForeignKey('owners.id'))
    amount = db.Column(db.Integer)
    winningBid = db.Column(db.Boolean, default=False)
    winningAmount = db.Column(db.Integer)

    player = db.relationship(Player, backref='bids')
    owner_bidding = db.relationship(Owner, backref='bids')
    draftPick = db.Column(db.Integer, default=None)
    bounty = db.Column(db.Boolean, default=False)  # use this to say whether bounty is money (True) or draftPick(False)

    def __init__(self, player_id, owner_bidding_id, amount, bounty=None):
        self.set_bid(player_id, owner_bidding_id, amount, bounty)

    def set_bid(self, player_id, owner_bidding_id, amount, bounty=None):
        self.player_id = player_id
        self.owner_bidding_id = owner_bidding_id
        self.amount = amount
        if bounty == 'money':
            self.bounty = True
        elif bounty is not None:
            self.draftPick = bounty

    def __repr__(self):
        player_name = Player.query.get(self.player_id).name
        owner_name = Owner.query.get(self.owner_bidding_id).team_name
        return '<Player: {0}; Bidding Team: {1}; Amount: ${2}>'.format(player_name, owner_name, self.amount)


class States(db.Model):
    __tablename__ = 'states'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(16))
    number = db.Column(db.Integer, default=None)
    bools = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return 'Name: {0}; number {1}; bools {2}'.format(self.name, self.number, self.bools)


class Score(db.Model):
    __tablename__ = 'scores'
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer)
    week = db.Column(db.Integer)
    score = db.Column(db.Numeric(5, 2))
    owner_id = db.Column(db.Integer, db.ForeignKey('owners.id'))
    owner = db.relationship(Owner, backref="scores")

    def __repr__(self):
        return 'Year: {0.year}\nWeek: {0.week}\nTeam: {0.owner.team_name}\nScore: {0.score}\n'.format(self)

    def __init__(self, mfl_team_id, score, week, year):
        self.add_score(mfl_team_id, score, week, year)

    def add_score(self, mfl_team_id, score, week, year):
        self.owner = Owner.query.filter_by(mfl_team_id=mfl_team_id).first()
        self.owner_id = self.owner.id
        self.score = score
        self.week = week
        self.year = year


class Division(db.Model):
    __tablename__ = 'division'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(16))
    teams = db.relationship(Owner, backref='division' )

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f'<{self.name}>'

class ProbowlRoster(db.Model):
    __tablename__ = 'probowl_roster'
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('owners.id'))
    qb = db.Column(db.Integer, db.ForeignKey('players.id'))
    rb1 = db.Column(db.Integer, db.ForeignKey('players.id'))
    rb2 = db.Column(db.Integer, db.ForeignKey('players.id'))
    wr1 = db.Column(db.Integer, db.ForeignKey('players.id'))
    wr2 = db.Column(db.Integer, db.ForeignKey('players.id'))
    wr3 = db.Column(db.Integer, db.ForeignKey('players.id'))
    te = db.Column(db.Integer, db.ForeignKey('players.id'))
    pk = db.Column(db.Integer, db.ForeignKey('players.id'))
    dst = db.Column(db.Integer, db.ForeignKey('players.id'))
    flex = db.Column(db.Integer, db.ForeignKey('players.id'))

    def __init__(self, owner):
        self.owner_id = owner

    def __repr__(self):
        return f'<Probowl Roster{self.owner_id}>'

    def update(self, players ):
        self.qb = int(players.get('QB')) if players.get('QB') else None
        self.rb1 = int(players.get('RB1')) if players.get('RB1') else None
        self.rb2 = int(players.get('RB2')) if players.get('RB2') else None
        self.wr1 = int(players.get('WR1')) if players.get('WR1') else None
        self.wr2 = int(players.get('WR2')) if players.get('WR2') else None
        self.wr3 = int(players.get('WR3')) if players.get('WR3') else None
        self.te = int(players.get('TE')) if players.get('TE') else None
        self.pk = int(players.get('PK')) if players.get('PK') else None
        self.dst = int(players.get('DEF')) if players.get('DEF') else None
        self.flex = int(players.get('FLEX')) if players.get('FLEX') else None

