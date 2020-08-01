import itertools
from flask import render_template, redirect, request, url_for, flash, session
from flask_login import login_required
from sqlalchemy.sql.expression import or_, and_

from app.models.owner import Owner
from app.models.player import Player
from constants import _TAGS, YEAR
from . import main
from .. import db


@main.route('/keepers', methods=['GET', 'POST'])
@login_required
def keepers():
    # pylint: disable=no-member

    return redirect(url_for('main.tags'))
    current_owner = Owner.query.get(session.get('owner').get('id'))
    if request.method == 'GET':
        if current_owner.keeperSet:
            roster = Player.query.filter_by(owner=current_owner).filter(
                or_(and_(Player.contractStatus == "K", Player.contractYear != "0"),
                    Player.tag.in_(_TAGS))).all()
            team_name = session.get('team_name')
            logo_url = session.get('owner').get('image_name')
            return render_template('keepers.html',
                                   roster=roster,
                                   teamname=team_name,
                                   logo_url=logo_url,
                                   keeperSet=True,
                                   year=YEAR)
        else:
            roster = Owner.query.filter_by(
                mfl_team_id=session.get('mfl_id')).first().players
            team_name = session.get('team_name')
            logo_url = session.get('owner').get('image_name')

            return render_template('keepers.html',
                                   roster=roster,
                                   teamname=team_name,
                                   logo_url=logo_url,
                                   keeperSet=False,
                                   year=YEAR)

    if request.method == 'POST':
        # Get list of players selected
        # filters to just submitted items
        players = {k: v for k, v in request.form.items() if v}
        # Verify keeper slots
        error = check_keeper_count(players)
        if error:
            return redirect(url_for('main.keepers'))
        else:  # A valid set of keepers and tags was submitted.
            # print(players, file=sys.stderr)
            for pid, tag in players.items():
                p = Player.query.get(pid)
                if tag in ['TRANS', 'FRAN', 'SFRAN']:
                    p.tag = tag
                    p.contractStatus = tag
                    # db.session.commit()
                elif tag == "K":
                    p.contractStatus = "K"
                    p.contractYear = "2"
                    # p.salary = p.salary + 5
                    # db.session.commit()
            current_owner.keeperSet = True
            db.session.commit()
            session['owner'] = current_owner.to_dict()

            return redirect(url_for('main.keepers'))


def check_keeper_count(players):
    error = False
    current_keeper_count = session.get('owner').get('keeperCount')
    posted_keeper_count = sum(1 for x in players.values() if x == 'K')
    posted_trans_count = sum(1 for x in players.values() if x == 'TRANS')
    posted_fran_count = sum(1 for x in players.values() if x == 'FRAN')
    posted_s_fran_count = sum(1 for x in players.values() if x == 'SFRAN')
    # print(current_keeper_count, posted_keeper_count)
    if current_keeper_count + posted_keeper_count > 2:
        if posted_keeper_count > 0:  # case where owner somehow has 3 keepers... me in 2017... Blake Bortles?  Idiot
            flash("Too many keepers were selected")
            error = True
    if posted_s_fran_count + posted_trans_count + posted_fran_count > 2:
        flash(
            "Too many tags.  At most 2 tags from Super Franchise, Franchise or Transition")
        error = True
    if posted_fran_count > 1:
        flash("Can only select Franchise tag once")
        error = True
    if posted_s_fran_count > 1:
        flash("Can only select Super Franchise tag once")
        error = True
    if posted_trans_count > 1:
        flash("Can only select Transition tag once")
        error = True
    return error


@main.route('/reset_keepers', methods=['POST'])
@login_required
def reset_keepers():
    # pylint: disable=no-member
    # get current owner
    current_owner = Owner.query.get(session.get('owner').get('id'))
    # get players that have tags or are k2s and reset
    tagged_players = Player.query.filter_by(
        owner=current_owner).filter(Player.tag.in_(_TAGS)).all()
    k2s = Player.query.filter_by(owner=current_owner).filter(
        and_(Player.contractStatus == "K", Player.contractYear == "2")).all()
    for p in itertools.chain(tagged_players, k2s):
        p.reset_contract_info(current_owner.mfl_team_id)
    current_owner.keeperSet = False
    db.session.commit()
    session['owner'] = current_owner.to_dict()
    return redirect(url_for('main.keepers'))
