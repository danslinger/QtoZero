from __future__ import print_function # In python 2.7
from flask import render_template, redirect, request, url_for, flash, session
from flask.ext.login import login_required, login_user, logout_user
from . import main
from .forms import LoginForm
from ..models import Owner, Player, Bid, DraftPick, States
from .. import db
from sqlalchemy.sql.expression import or_,and_
import sys
# from ..bidding import highestBid
from operator import attrgetter
from SlackBot import SlackBot
from TaskScheduler import TaskScheduler
import datetime, subprocess

bot = SlackBot()
ts = TaskScheduler()
letBotPost = True

image_host = "https://darkwater80.github.io/IMAGES/ICONS/2017/"
_TAGS = ['FRAN', 'SFRAN', 'TRANS']


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
            # session['owner_object'] = owner #stop doing this!! You can't serialize the owner object (well, maybe.  You can look into that) BUT STOP TRYING THIS
            # flash('You were successfully logged in')
            return redirect(request.args.get('next') or url_for('main.index'))
        else:
            flash('Incorrect Email or Password')
    return render_template('login.html', form=form)

@main.route('/')
@login_required
def index():
    roster = Owner.query.filter_by(mfl_team_id=session['mfl_id']).first().players
    teamname = session.get('owner').get('team_name')
    logo_url = image_host + session.get('owner').get('image_name')
    availablePlayers = Player.query.filter(or_(Player.contractStatus == "T", Player.contractStatus == "F"))
    return render_template('index.html', 
                            roster=roster,
                            teamname=teamname,
                            logo_url=logo_url,
                            availablePlayers=availablePlayers)

@main.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main.route('/contacts')
@login_required
def contacts():
    owners = Owner.query.all()
    return render_template('contacts.html', 
                            owners=owners,
                            image_host=image_host)


@main.route('/keepers', methods=['GET', 'POST'])
@login_required
def keepers():
    # return redirect(url_for('main.tags'))
    current_owner = Owner.query.get(session.get('owner').get('id'))
    error = False

    if request.method == 'GET':
        if current_owner.keeperSet == True:
            roster = Player.query.filter_by(owner=current_owner).filter(
                      or_(and_(Player.contractStatus == "K", Player.contractYear == "2"),
                          Player.tag.in_(_TAGS))).all()
            teamname = session.get('team_name')
            logo_url = image_host + session.get('owner').get('image_name')
            return render_template('keepers.html', 
                            roster=roster,
                            teamname=teamname,
                            logo_url=logo_url,
                            keeperSet=True)
        else:
            roster = Owner.query.filter_by(mfl_team_id=session.get('mfl_id')).first().players
            teamname = session.get('team_name')
            logo_url = image_host + session.get('owner').get('image_name')

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
        print (currentKeeperCount, postedKeeperCount)
        if currentKeeperCount + postedKeeperCount > 2:
            if postedKeeperCount > 0:  # case where owner somehow has 3 keepers... me in 2017... Blake Bortels?  Idiot. 
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

@main.route('/tags')
@login_required
def tags():
    fplayers = Player.query.filter(Player.tag=="FRAN").all()
    tplayers = Player.query.filter(Player.tag=="TRANS").all()
    sfplayers = Player.query.filter(Player.tag=="SFRAN").all()
    k2players = Player.query.filter(Player.contractYear=="2").all()
    k1players = Player.query.filter(and_(Player.contractStatus=="K", Player.contractYear=="1")).all()


    return render_template('tagged_players.html', 
        fplayers=fplayers,
        tplayers=tplayers,
        sfplayers=sfplayers,
        k2players=k2players,
        k1players=k1players
        )

@main.route('/reset_keepers', methods=['POST'])
@login_required
def reset_keepers():
    #get current owner
    current_owner = Owner.query.get(session.get('owner').get('id'))
    #get players that have tags and reset
    tagged_players = Player.query.filter_by(owner=current_owner).filter(Player.tag.in_(_TAGS)).all()
    for p in tagged_players:
        p.ResetContractInfo(current_owner.mfl_team_id)
        # p.tag = None
        # p.contractStatus = "S"
        # p.contractYear = "0"
        # db.session.commit()
    #get players that have K2 and reset
    k2s = Player.query.filter_by(owner=current_owner).filter(and_(Player.contractStatus == "K", Player.contractYear == "2")).all()
    for p in k2s:
        p.ResetContractInfo(current_owner.mfl_team_id)
        # p.contractStatus = "S"
        # p.contractYear = "0"
        # p.salary = p.salary - 5
        # db.session.commit()
    current_owner.keeperSet = False
    db.session.commit()
    session['owner'] = current_owner.to_dict()
    return redirect(url_for('main.keepers'))

@main.route('/bidding', methods=['GET', 'POST'])
@login_required
def bidding():
    biddingOn = States.query.filter(States.name == 'biddingOn').scalar().bools
    if biddingOn:
        transPlayer = Player.query.filter(Player.upForBid == True).filter(Player.tag == "TRANS").scalar()
        franPlayer = Player.query.filter(Player.upForBid == True).filter(Player.tag == "FRAN").scalar()
        current_owner = Owner.query.get(session.get('owner').get('id'))
        if current_owner.madeBid:
            tBid = Bid.query.filter(Bid.player_id == transPlayer.id)\
                            .filter(Bid.owner_bidding_id == current_owner.id)\
                            .scalar()
            fBid = Bid.query.filter(Bid.player_id == franPlayer.id)\
                            .filter(Bid.owner_bidding_id == current_owner.id)\
                            .scalar()
        else:
            tBid = None
            fBid = None

        if request.method == 'GET':
            round1Picks = [pick.pickInRound for pick in current_owner.draftPicks.filter(DraftPick.draftRound == 1).all()]
            round2Picks = [pick.pickInRound for pick in current_owner.draftPicks.filter(DraftPick.draftRound == 2).all()]
            return render_template('bidding.html', 
                    transPlayer=transPlayer,
                    franPlayer=franPlayer,
                    biddingOn=biddingOn,
                    tBid=tBid,
                    fBid=fBid,
                    madeBid=current_owner.madeBid,
                    round1Picks=round1Picks,
                    round2Picks=round2Picks,
                    )

        if request.method == 'POST':
            # This is where you make a bid, set that the owner made a bid, then return stuff for the bidding page that indicates the owner has made a bid on a player       
            franPlayerBid = int(request.form.get('franPlayerBid') or 0)
            transPlayerBid = int(request.form.get('transPlayerBid') or 0)
            franBounty = request.form.get('franBounty') or None
            transBounty = request.form.get('transBounty') or None


            if not franPlayerBid and not transPlayerBid:
                flash("You didn't enter a bid for either player.")
                return redirect(url_for('main.bidding'))

            if transBounty != 'money' and transBounty is not None:
                transBounty = int(transBounty)
            if franBounty != 'money' and franBounty is not None:
                franBounty = int(franBounty)
            
            invalidBid = False    
            # Check if owner has draft pick available
            # if not current_owner.hasPick(1) and franPlayerBid:
            #     flash("You don't have a first round pick.  Cannot bid on a Franchise Player")
            #     invalidBid = True
            # if not current_owner.hasPick(2) and transPlayerBid:
            #     flash("You don't have a second round pick.  Cannot bid on a Transition Player")
            #     invalidBid = True
            if franPlayerBid > 0 and franPlayerBid < 30: 
                flash("Minimum bid for a Franchise Player is $30")
                invalidBid = True

            if transPlayerBid < 20 and transPlayerBid > 0:
                flash("Minimum bid for a Transition Player is $20")
                invalidBid = True
            if transPlayerBid > 100 or franPlayerBid > 100:
                flash("Over $100?  Really?  This isn't Brandon Jackson.  Try again...")
                invalidBid = True
            
            if invalidBid:
                return redirect(url_for('main.bidding'))
            else:
                tBid = Bid(player_id=transPlayer.id, owner_bidding_id=current_owner.id, amount=transPlayerBid, bounty=transBounty)
                fBid = Bid(player_id=franPlayer.id, owner_bidding_id=current_owner.id, amount=franPlayerBid, bounty=franBounty)
                db.session.add_all([tBid, fBid])

                current_owner.madeBid = True
                session['owner'] = current_owner.to_dict()
                
                db.session.commit()
                return redirect(url_for('main.bidding'))
    else: #bidding is off.  redirect to 'matching' page, or whatever I'll call it
        # return "Bidding is off right now.  Just go back."
        return redirect(url_for('main.match'))

@main.route('/reset_bids', methods=['POST'])
@login_required
def reset_bids():
    transPlayer = Player.query.filter(Player.upForBid == True).filter(Player.tag == "TRANS").scalar()
    franPlayer = Player.query.filter(Player.upForBid == True).filter(Player.tag == "FRAN").scalar()
    current_owner = Owner.query.get(session.get('owner').get('id'))

    #find bid for transPlayer with current_owner, delete it
    tBid = Bid.query.filter(Bid.player_id == transPlayer.id).filter(Bid.owner_bidding_id == session.get('owner').get('id')).scalar()
    db.session.delete(tBid)    
    #find bid for franPlayer with current_owner, delete it
    fBid = Bid.query.filter(Bid.player_id == franPlayer.id).filter(Bid.owner_bidding_id == session.get('owner').get('id')).scalar()
    db.session.delete(fBid)

    current_owner.madeBid = False
    session['owner'] = current_owner.to_dict()
    db.session.commit()
    return redirect(url_for('main.bidding'))

@main.route('/match', methods=['GET'])
@login_required
def match():
    biddingOn = States.query.filter(States.name == 'biddingOn').scalar().bools
    franchiseDecisionMade = States.query.filter(States.name == 'franchiseDecisionMade').scalar().bools
    transitionDecisionMade = States.query.filter(States.name == 'transitionDecisionMade').scalar().bools
    if biddingOn: #make sure no one comes here on accident
        return redirect(url_for('main.bidding'))
    else:
        #get the current players up for bid
        transPlayer = Player.query.filter(Player.upForBid == True).filter(Player.tag == "TRANS").scalar()
        franPlayer = Player.query.filter(Player.upForBid == True).filter(Player.tag == "FRAN").scalar()
        
        # get the winning transition and franchise bids
        # bidding.py stopBid() should have run, so can get winning bid via queries
        winningTransBid = Bid.query.filter(Bid.player_id == transPlayer.id).filter(Bid.winningBid == True).scalar()
        winningFranBid = Bid.query.filter(Bid.player_id == franPlayer.id).filter(Bid.winningBid == True).scalar()
               
        return render_template('match.html',
                            transPlayer=transPlayer,
                            franPlayer=franPlayer,
                            tBid=winningTransBid,
                            fBid=winningFranBid,
                            franchiseDecisionMade=franchiseDecisionMade,
                            transitionDecisionMade=transitionDecisionMade,
                            )
@main.route('/matchTrans', methods=['POST'])
@login_required
def matchTrans():
    transPlayer = Player.query.filter(Player.upForBid == True).filter(Player.tag == "TRANS").scalar()
    winningTransBid = Bid.query.filter(Bid.player_id == transPlayer.id).filter(Bid.winningBid == True).scalar()
    winningPick = winningFranBid.draftPick
    current_owner = Owner.query.get(transPlayer.owner.id)
    bidding_owner = Owner.query.get(winningTransBid.owner_bidding_id)

    decision = request.form.get('transMatch')
    if decision == 'match': #keep player
        # could do lots of things... but really don't need to do anything
        message = "{0} has decided to keep {1} at a price of ${2}." \
                  .format(current_owner.team_name,
                          transPlayer.name,
                          winningTransBid.amount
                    )
    else: #release player
        transPlayer.updateOwner(bidding_owner.id)
        if winningPick:
            DraftPick.query.filter(and_(DraftPick.pickInRound == winningPick, DraftPick.draftRound ==2)).scalar().updatePick(current_owner.id)
        message = "{0} has decided to let {1} take his talents to {2}." \
                   .format(current_owner.team_name,
                           transPlayer.name,
                           bidding_owner.team_name)

    transitionDecisionMade = States.query.filter(States.name == 'transitionDecisionMade').scalar()
    transitionDecisionMade.bools = True
    db.session.commit()
    bothDecisions = getBothDecisions()
    if bothDecisions == True:
        # get start bid job and redo it so it happens now
        # startTime = datetime.datetime.today() + datetime.timedelta(minutes=2)
        # startJob = ts.getJob('STARTBID')
        # ts.setJob(startJob, startTime)

        subprocess.call(['/var/www/Calvinball/Calvinball/venv/bin/python2', '/var/www/Calvinball/Calvinball/bidding.py', 'startBid'])


    if letBotPost:
        bot.postMessage('general', message)
    else:
        print(message)
    return redirect(url_for('main.match'))

@main.route('/matchFran', methods=['POST'])
@login_required
def matchFran():
    franPlayer = Player.query.filter(Player.upForBid == True).filter(Player.tag == "FRAN").scalar()
    winningFranBid = Bid.query.filter(Bid.player_id == franPlayer.id).filter(Bid.winningBid == True).scalar()
    winningPick = winningFranBid.draftPick
    current_owner = Owner.query.get(franPlayer.owner.id)
    bidding_owner = Owner.query.get(winningFranBid.owner_bidding_id)

    decision = request.form.get('franMatch')
    if decision == 'match': #keep player
        # could do lots of things... but really don't need to do anything
        message = "{0} has decided to keep {1} at a price of ${2}." \
                  .format(current_owner.team_name,
                          franPlayer.name,
                          winningFranBid.amount
                    )
    else: #release player
        franPlayer.updateOwner(bidding_owner.id)
        if winningPick:
            DraftPick.query.filter(and_(DraftPick.pickInRound == winningPick, DraftPick.draftRound ==1)).scalar().updatePick(current_owner.id)
        message = "{0} has decided to let {1} take his talents to {2}." \
                   .format(current_owner.team_name,
                           franPlayer.name,
                           bidding_owner.team_name)

    franchiseDecisionMade = States.query.filter(States.name == 'franchiseDecisionMade').scalar()
    franchiseDecisionMade.bools = True
    db.session.commit()
    bothDecisions = getBothDecisions()
    try:
        if bothDecisions == True:
            # get start bid job and redo it so it happens now
            startTime = datetime.datetime.today() + datetime.timedelta(minutes=2)
            startJob = ts.getJob('STARTBID')
            ts.setJob(startJob, startTime)
    except Exception as e:
        message += "\n\nDANNY!  You need to fix something dumb ass!"
    
    if letBotPost:
        bot.postMessage('general', message)
    else:
        print(message)
    return redirect(url_for('main.match'))

@main.route('/draft_order', methods=['GET'])
@login_required
def draft_order():
    draftPicks = DraftPick.query.all()
    return render_template('draftOrder.html', draftPicks=draftPicks)

def getBothDecisions():
    franchiseDecisionMade = States.query.filter(States.name == 'franchiseDecisionMade').scalar().bools
    transitionDecisionMade = States.query.filter(States.name == 'transitionDecisionMade').scalar().bools
    return franchiseDecisionMade and transitionDecisionMade

