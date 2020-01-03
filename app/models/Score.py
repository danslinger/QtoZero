from .. import db


class Score(db.Model):
    __tablename__ = 'scores'
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer)
    week = db.Column(db.Integer)
    score = db.Column(db.Numeric(5, 2))
    owner_id = db.Column(db.Integer, db.ForeignKey('owners.id'))
    owner = db.relationship('Owner', backref="scores")

    def __repr__(self):
        return 'Year: {0.year}\nWeek: {0.week}\nTeam: {0.owner.team_name}\nScore: {0.score}\n'.format(self)

    def __init__(self, mfl_team_id, score, week, year):
        self.add_score(mfl_team_id, score, week, year)

    def add_score(self, mfl_team_id, score, week, year):
        # FIXME
        # self.owner = Owner.query.filter_by(mfl_team_id=mfl_team_id).first()
        # self.owner_id = self.owner.id
        self.score = score
        self.week = week
        self.year = year
