from .. import db


class DraftPick(db.Model):
     # pylint: disable=no-member
    __tablename__ = "draftpicks"
    id = db.Column(db.Integer, primary_key=True)
    draftRound = db.Column(db.Integer)
    pickInRound = db.Column(db.Integer)
    owner_id = db.Column(db.Integer, db.ForeignKey('owners.id'))

    def update_pick(self, new_owner_id):
        self.owner_id = new_owner_id

    def __repr__(self):
        owner_name = self.owner.name
        return '<Round:{0}; Pick:{1}; Owner:{2}>'.format(self.draftRound, self.pickInRound, owner_name)
