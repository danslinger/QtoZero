#!/usr/bin/env python
import os
from flask_migrate import Migrate
from app import create_app, db
from app.models.owner import Owner
from app.models.player import Player
from app.models.draft_pick import DraftPick
from app.models.bid import Bid
from app.models.states import States
from app.models.score import Score
from app.models.division import Division
from app.models.pro_bowl_roster import ProbowlRoster
app = create_app(os.getenv('FLASK_CONFIG') or 'default')

migrate = Migrate(app, db)


@app.shell_context_processor
def make_shell_context():
    return dict(app=app,
                db=db,
                Owner=Owner,
                Player=Player,
                Bid=Bid,
                DraftPick=DraftPick,
                States=States,
                Score=Score,
                Division=Division,
                ProbowlRoster=ProbowlRoster)
