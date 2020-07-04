from .. import db


class Bid(db.Model):
    # pylint: disable=no-member
    __tablename__ = "bids"
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'))
    owner_bidding_id = db.Column(db.Integer, db.ForeignKey('owners.id'))
    amount = db.Column(db.Integer)
    winningBid = db.Column(db.Boolean, default=False)
    winningAmount = db.Column(db.Integer)

    player = db.relationship('Player', backref='bids')
    owner_bidding = db.relationship('Owner', backref='bids')
    draftPick = db.Column(db.Integer, default=None)
    # use this to say whether bounty is money (True) or draftPick(False)
    bounty = db.Column(db.Boolean, default=False)

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
        player_name = self.player.name
        owner_name = self.owner_bidding.team_name
        return '<Player: {0}; Bidding Team: {1}; Amount: ${2}>'.format(player_name, owner_name, self.amount)
