from werkzeug.security import generate_password_hash, check_password_hash
from flask.ext.login import UserMixin
from sqlalchemy.sql.expression import or_,and_
from . import db, login_manager
import requests, json
from tokens import tokens

league_id = 31348
url = 'http://www55.myfantasyleague.com/2018/export'
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

    @property
    def password(self):
        return AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def keepers(self):
        return self.players.filter(and_(Player.contractStatus=="K", Player.contractYear == "1")).count()
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
        }
        return d
    def hasPick(self, rd):
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
    status = db.Column(db.String(16)) # ROSTER, TAXI_SQUAD, INJURED_RESERVE 
    contractYear = db.Column(db.String(16))
    tag = db.Column(db.String(8)) # [TRANS, FRAN, SUPER_FRAN]
    upForBid = db.Column(db.Boolean, default=False)
    finishedBidding = db.Column(db.Boolean, default=False)

    def __init__(self, mfl_dict):
        self.updatePlayer(mfl_dict)

    def updatePlayer(self, mfl_dict):
        self.name = self.name_swap(mfl_dict.get('name')) #Expects last,first
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

    def updateContractInfo(self, contractInfo):
        self.contractYear = contractInfo.get('contractYear')
        self.contractStatus = contractInfo.get('contractStatus')
        self.status = contractInfo.get('status') or "FA"
        self.salary = contractInfo.get('salary') 

    def ResetContractInfo(self, currentOwnerID):
        payload = {'TYPE': 'rosters',
                    'JSON': 1,
                    'L': league_id,
                    'FRANCHISE': currentOwnerID,
                    'APIKEY': api_token,
                  }
        r = requests.get(url, params=payload)
        roster = json.loads(r.content)
        for data in roster['rosters']['franchise']['player']:
            if data.get('id') == self.mfl_id:
                self.updateContractInfo(data)
                self.tag = None
                break

    def updateRosterInfo(self, contractInfo, mfl_id):
        '''
        contractInfo contains a dictionary in the form:
        {
            "contractYear": "2" # Josh changed this to be the total years of the contract, which messed me up and is stupid
            "contractStatus": "K", # or T or F or S
            "status": "ROSTER",
            "id": "11175",
            "salary": "15"
            "contractInfo": 1 # represents the years remaining on the contract
        }
        mfl_id is the mfl_id of the owner.  Need to take this value and find
        the owner.id and assign that to the Player.mfl_team (the foreign key is to owner.id)

        **maybe change mfl_team to owner NOPE, because of the backref owner**
        '''
        self.contractYear = contractInfo.get('contractInfo')
        self.contractStatus = contractInfo.get('contractStatus')
        self.status = contractInfo.get('status') or "FA"    #all should have this.  Not sure why I added or "FA"
        self.salary = contractInfo.get('salary')
        self.mfl_team = self.setMFLTeamFromMFLID(mfl_id)
        print self.name, contractInfo.get('contractYear'), contractInfo.get('contractStatus')

    def updateOwner(self, new_owner_id):
        self.previous_owner_id = self.mfl_team
        self.mfl_team = new_owner_id

    def setMFLTeamFromMFLID(self, mfl_id):
        return Owner.query.filter_by(mfl_team_id=mfl_id).first().id

    def name_swap(self, name_str):
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

    def updatePick(self, new_owner_id):
        self.owner_id = new_owner_id

    def __repr__(self):
        ownerName = Owner.query.get(self.owner_id)
        return '<Round:{0}; Pick:{1}; Owner:{2}>'.format(self.draftRound, self.pickInRound, ownerName)


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
    bounty = db.Column(db.Boolean, default=False) # use this to say whether bounty is money (True) or draftPick(False)

    def __init__(self, player_id, owner_bidding_id, amount, bounty=None):
        self.setBid(player_id, owner_bidding_id, amount, bounty)

    def setBid(self, player_id, owner_bidding_id, amount, bounty=None):
        self.player_id = player_id
        self.owner_bidding_id = owner_bidding_id
        self.amount = amount
        if bounty == 'money':
            self.bounty = True
        elif bounty is not None:
            self.draftPick = bounty

    def __repr__(self):
        playerName = Player.query.get(self.player_id).name
        ownerName = Owner.query.get(self.owner_bidding_id).team_name
        return '<Player: {0}; Bidding Team: {1}; Amount: ${2}>'.format(playerName, ownerName, self.amount)

class States(db.Model):
    __tablename__ = 'states'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(16))
    number = db.Column(db.Integer, default=None)
    bools = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return 'Name: {0}; number {1}; bools {2}'.format(self.name, self.number, self.bools)