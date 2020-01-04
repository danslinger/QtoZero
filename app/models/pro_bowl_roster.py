from .. import db


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

    def update(self, players):
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
