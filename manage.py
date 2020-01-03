#!/usr/bin/env python
import os
from flask_migrate import Migrate
from app import create_app, db
from app.models.Owner import Owner
from app.models.Player import Player
from app.models.DraftPick import DraftPick
from app.models.Bid import Bid
from app.models.States import States
from app.models.Score import Score
from app.models.Division import Division
from app.models.ProbowlRoster import ProbowlRoster
app = create_app(os.getenv('FLASK_CONFIG') or 'default')

migrate = Migrate(app, db)


@app.shell_context_processor
def make_shell_context():
    return dict(app=app, db=db, Owner=Owner, Player=Player, Bid=Bid, DraftPick=DraftPick, States=States, Score=Score, Division=Division, ProbowlRoster=ProbowlRoster)
