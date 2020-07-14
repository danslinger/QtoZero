from flask import render_template, redirect, request, url_for, flash, session
from flask_login import login_required, login_user, logout_user
from sqlalchemy.sql.expression import or_

from app.models.owner import Owner
from app.models.player import Player
from . import main
from .forms import LoginForm


@main.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        owner = Owner.query.filter_by(email=form.email.data.lower()).first()
        if owner is not None and owner.verify_password(form.password.data):
            login_user(owner, form.remember_me.data)
            session['team_name'] = owner.team_name
            session['mfl_id'] = owner.mfl_team_id
            session['name'] = owner.name
            session['owner'] = owner.to_dict()
            # session['owner_object'] = owner #stop doing this!! You can't serialize the owner object
            # (well, maybe.  You can look into that) BUT STOP TRYING THIS
            # flash('You were successfully logged in')
            return redirect(request.args.get('next') or url_for('main.index'))
        else:
            flash('Incorrect Email or Password')
    return render_template('login.html', form=form)


@main.route('/')
@login_required
def index():
    roster = Owner.query.filter_by(
        mfl_team_id=session['mfl_id']).first().players
    team_name = session.get('owner').get('team_name')
    logo_url = session.get('owner').get('image_name')
    available_players = Player.query.filter(
        or_(Player.contractStatus == "T", Player.contractStatus == "F"))
    return render_template('index.html',
                           roster=roster,
                           teamname=team_name,
                           logo_url=logo_url,
                           availablePlayers=available_players)


@main.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.login'))
