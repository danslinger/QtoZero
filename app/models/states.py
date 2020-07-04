from .. import db


class States(db.Model):
    __tablename__ = 'states'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(16))
    number = db.Column(db.Integer, default=None)
    bools = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return 'Name: {0}; number {1}; bools {2}'.format(self.name, self.number, self.bools)
