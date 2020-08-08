import datetime
from flask import render_template, redirect, request, url_for, flash, session
from flask_login import login_required
from app.models.owner import Owner
from app.models.player import Player
from app.models.pro_bowl_roster import ProbowlRoster
from app.models.division import Division
from . import main
from .. import db


@main.route('/probowl', methods=['GET'])
@login_required
def probowl():
    return redirect(url_for('main.index'))
    current_owner = Owner.query.get(session.get('owner').get('id'))
    division = Division.query.get(current_owner.division_id)
    positions = ['QB', 'RB', 'WR', 'TE', 'PK', 'Def']
    results = dict()

    for position in positions:
        results[position] = Player.query.join(Owner).join(Division).filter(Division.name == division.name) \
            .filter(Player.position == position).all()

    results['FLEX'] = results['RB'] + results['WR'] + results['TE']
    current_owner_id = session.get('owner').get('id')
    pb_roster = ProbowlRoster.query.filter(
        ProbowlRoster.owner_id == current_owner_id).first()

    return render_template('probowl.html', players=results, pb_roster=pb_roster)


@main.route('/probowl/setLineup', methods=['POST'])
def set_probowl_lineup():
    cutoff_time = datetime.datetime(2019, 12, 29, 10)
    if datetime.datetime.now() > cutoff_time:
        flash("Games started.  Can't submit roster changes")
    else:
        players = {k: v for k, v in request.form.items() if v}
        print(players)
        current_owner_id = session.get('owner').get('id')
        pb_roster = ProbowlRoster.query.filter(
            ProbowlRoster.owner_id == current_owner_id).first()
        if not pb_roster:
            pb_roster = ProbowlRoster(current_owner_id)
        pb_roster.update(players)
        db.session.add(pb_roster)
        db.session.commit()
        flash("Pro Bowl Roster Submitted Successfully")
    return redirect(url_for('main.probowl'))
