from flask_login import login_required
from flask import render_template
from sqlalchemy.sql.expression import and_

from app.models.player import Player
from . import main
from constants import YEAR


@main.route('/tags')
@login_required
def tags():
    fran_players = Player.query.filter(Player.tag == "FRAN").all()
    trans_players = Player.query.filter(Player.tag == "TRANS").all()
    super_fran_players = Player.query.filter(Player.tag == "SFRAN").all()
    k2players = Player.query.filter(Player.contractYear == "2").all()
    k1players = Player.query.filter(
        and_(Player.contractStatus == "K", Player.contractYear == "1")).all()

    return render_template('tagged_players.html',
                           fplayers=fran_players,
                           tplayers=trans_players,
                           sfplayers=super_fran_players,
                           k2players=k2players,
                           k1players=k1players,
                           currentYear=YEAR,
                           lastYear=YEAR-1
                           )
