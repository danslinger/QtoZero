from .. import db


class Division(db.Model):
    __tablename__ = 'division'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(16))
    teams = db.relationship('Owner', backref='division')

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f'<{self.name}>'
