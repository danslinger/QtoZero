from __future__ import print_function # In python 2.7
from flask import render_template, redirect, request, url_for, flash, session
from flask.ext.login import login_required, login_user, logout_user
from . import main
from .forms import LoginForm
from ..models import Owner, Player, Bid, DraftPick
from .. import db
from sqlalchemy.sql.expression import or_
import sys

image_year = "_2016.png"

@main.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        owner = Owner.query.filter_by(email=form.email.data).first()
        if owner is not None and owner.verify_password(form.password.data):
            login_user(owner, form.remember_me.data)
            session['team_name'] = owner.team_name
            session['mfl_id'] = owner.mfl_team_id
            session['name'] = owner.name
            session['owner'] = owner.to_dict()
            session['owner_object'] = owner
            # flash('You were successfully logged in')
            return redirect(request.args.get('next') or url_for('main.index'))
        else:
            flash('Incorrect Email or Password')
    return render_template('login.html', form=form)

# @main.route('/')
# @login_required
# def index():
#     roster = getRoster(session.get('mfl_id'))
#     teamname = session.get('team_name')
#     logo_url = session.get('name').upper().replace(" ", "_") + "_2015.png"
#     return render_template('index.html', 
#                             roster=roster,
#                             teamname=teamname,
#                             logo_url=logo_url)

@main.route('/')
@login_required
def index():
    roster = Owner.query.filter_by(mfl_team_id=session['mfl_id']).first().players
    # teamname = session.get('team_name')
    teamname = session.get('owner').get('team_name')
    # logo_url = session.get('name').upper().replace(" ", "_") + "_2015.png"
    logo_url = session.get('owner').get('name').upper().replace(" ", "_") + image_year
    return render_template('index.html', 
                            roster=roster,
                            teamname=teamname,
                            logo_url=logo_url)

@main.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main.route('/contacts')
@login_required
def contacts():
    owners = Owner.query.all()
    return render_template('contacts.html', owners=owners)


@main.route('/keepers', methods=['GET', 'POST'])
@login_required
def keepers():
    current_owner = Owner.query.get(session.get('owner').get('id'))
    error = False
    _TAGS = ['FRAN', 'SFRAN', 'TRANS']
    _K = ['K2', 'K1']

    if request.method == 'GET':
        if current_owner.keeperSet == True:
            roster = Player.query.filter_by(owner=current_owner).filter(or_(Player.contractStatus.in_(_K), Player.tag.in_(_TAGS))).all()
            teamname = session.get('team_name')
            logo_url = session.get('name').upper().replace(" ", "_") + image_year
            return render_template('keepers.html', 
                            roster=roster,
                            teamname=teamname,
                            logo_url=logo_url,
                            keeperSet=True)
        else:
            roster = Owner.query.filter_by(mfl_team_id=session.get('mfl_id')).first().players
            teamname = session.get('team_name')
            logo_url = session.get('name').upper().replace(" ", "_") + image_year
            # flash("This is a test flash")
            return render_template('keepers.html', 
                            roster=roster,
                            teamname=teamname,
                            logo_url=logo_url,
                            keeperSet=False)

    if request.method == 'POST':
        # Get list of players selected
        players = {k:v for k,v in request.form.iteritems() if v} #filters to just submitted items
        # Verify keeper slots
        currentKeeperCount = session.get('owner').get('keeperCount')
        postedKeeperCount = sum(1 for x in players.values() if x == 'K')
        postedTransCount = sum(1 for x in players.values() if x == 'TRANS')
        postedFranCount = sum(1 for x in players.values() if x == 'FRAN')
        postedSFranCount = sum(1 for x in players.values() if x == 'SFRAN')
        if currentKeeperCount + postedKeeperCount > 2:
            flash("Too many keepers were selected")
            error = True
        if postedSFranCount + postedTransCount + postedFranCount > 2:
            flash("Too many tags.  At most 2 tags from Super Franchise, Franchise or Transition")
            error = True
        if postedFranCount > 1:
            flash("Can only select Franchise tag once")
            error = True
        if postedSFranCount > 1:
            flash("Can only select Super Franchise tag once")
            error = True
        if postedTransCount > 1:
            flash("Can only select Transition tag once")
            error = True
        if error:
            return redirect(url_for('main.keepers'))
        else: #A valid set of keepers and tags was submitted.  
            # print(players, file=sys.stderr)
            for pid,tag in players.iteritems():
                p = Player.query.get(pid)
                if tag in ['TRANS', 'FRAN', 'SFRAN']:
                    p.tag = tag
                    p.contractStatus = tag
                    db.session.commit()
                elif tag == "K":
                    p.contractStatus = "K2"
                    p.salary = p.salary + 5
                    db.session.commit()
            current_owner.keeperSet = True
            db.session.commit()
            session['owner'] = current_owner.to_dict()

            
            return redirect(url_for('main.keepers'))

        
        # Verify tags < 2 and 1 of each tag type
        # Apply the data for the keepers
        # 
    
@main.route('/reset_keepers', methods=['POST'])
@login_required
def reset_keepers():
    #get current owner
    _TAGS = ['FRAN', 'SFRAN', 'TRANS']
    current_owner = Owner.query.get(session.get('owner').get('id'))
    #get players that have tags and reset
    tagged_players = Player.query.filter_by(owner=current_owner).filter(Player.tag.in_(_TAGS)).all()
    for p in tagged_players:
        p.tag = ""
        p.contractStatus = "S1"
        db.session.commit()
    #get players that have K2 and reset
    k2s = Player.query.filter_by(owner=current_owner).filter(Player.contractStatus.in_(["K2"])).all()
    for p in k2s:
        p.contractStatus = "S1"
        p.salary = p.salary - 5
        db.session.commit()
    current_owner.keeperSet = False
    db.session.commit()
    return redirect(url_for('main.keepers'))

@main.route('/bidding', methods=['GET', 'POST'])
@login_required
def bidding():
    
    transPlayer = Player.query.filter(Player.upForBid == True).filter(Player.tag == "TRANS").scalar()
    franPlayer = Player.query.filter(Player.upForBid == True).filter(Player.tag == "FRAN").scalar()
    bidIn = session.get('owner').get('madeBid')

    if request.method == 'GET':

        return render_template('bidding.html', 
                transPlayer=transPlayer,
                franPlayer=franPlayer,
                bidIn = bidIn
                )

    if request.method == 'POST':
        franPlayerBid = request.form.get('franPlayerBid')
        transPlayerBid = request.form.get('transPlayerBid')

        # This is where you make a bid, set that the owner made a bid, then return stuff for the bidding page that indicates the owner has made a bid on a player
        

        return render_template('bidding.html', 
                transPlayer=transPlayer,
                franPlayer=franPlayer,
                bidIn = bidIn,
                franPlayerBid=franPlayerBid
                )