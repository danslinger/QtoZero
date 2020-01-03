from flask_login import UserMixin
from sqlalchemy.sql.expression import and_
from werkzeug.security import generate_password_hash, check_password_hash

from .. import db, login_manager


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
        # FIXME
        return
        # # pylint: disable=no-member
        # return self.players.filter(and_(Player.contractStatus == "K", Player.contractYear == "1")).count()
        # # write a query to return the number of keepers on a roster

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

    # def has_pick(self, rd):
        # FIXME
        # pylint: disable=no-member
        # picks = self.draftPicks.filter(DraftPick.draftRound == rd).all()
        # if picks:
        #     return True
        # else:
        #     return False

    def __repr__(self):
        return '<Owner %r>' % self.team_name


@login_manager.user_loader
def load_user(user_id):
    return Owner.query.get(int(user_id))
