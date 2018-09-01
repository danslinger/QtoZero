import itertools
import subprocess

from flask import render_template, redirect, request, url_for, flash, session
from flask_login import login_required, login_user, logout_user
from sqlalchemy.sql.expression import or_, and_

# from ..bidding import highest_bid
from SlackBot import SlackBot
from . import main
from .forms import LoginForm
from .. import db
from ..models import Owner, Player, Bid, DraftPick, States
from ...local_settings import let_bot_post

bot = SlackBot()
# ts = TaskScheduler()
letBotPost = let_bot_post

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
    roster = Owner.query.filter_by(mfl_team_id=session['mfl_id']).first().players
    team_name = session.get('owner').get('team_name')
    logo_url = image_host + session.get('owner').get('image_name')
    available_players = Player.query.filter(or_(Player.contractStatus == "T", Player.contractStatus == "F"))
    return render_template('index.html',
                           roster=roster,
                           teamname=team_name,
                           logo_url=logo_url,
                           availablePlayers=available_players)


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
    if request.method == 'GET':
        if current_owner.keeperSet:
            roster = Player.query.filter_by(owner=current_owner).filter(
                or_(and_(Player.contractStatus == "K", Player.contractYear == "2"),
                    Player.tag.in_(_TAGS))).all()
            team_name = session.get('team_name')
            logo_url = image_host + session.get('owner').get('image_name')
            return render_template('keepers.html',
                                   roster=roster,
                                   teamname=team_name,
                                   logo_url=logo_url,
                                   keeperSet=True)
        else:
            roster = Owner.query.filter_by(mfl_team_id=session.get('mfl_id')).first().players
            team_name = session.get('team_name')
            logo_url = image_host + session.get('owner').get('image_name')

            return render_template('keepers.html',
                                   roster=roster,
                                   teamname=team_name,
                                   logo_url=logo_url,
                                   keeperSet=False)

    if request.method == 'POST':
        # Get list of players selected
        players = {k: v for k, v in request.form.items() if v}  # filters to just submitted items
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
        flash("Too many tags.  At most 2 tags from Super Franchise, Franchise or Transition")
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


@main.route('/tags')
@login_required
def tags():
    fran_players = Player.query.filter(Player.tag == "FRAN").all()
    trans_players = Player.query.filter(Player.tag == "TRANS").all()
    super_fran_players = Player.query.filter(Player.tag == "SFRAN").all()
    k2players = Player.query.filter(Player.contractYear == "2").all()
    k1players = Player.query.filter(and_(Player.contractStatus == "K", Player.contractYear == "1")).all()

    return render_template('tagged_players.html',
                           fplayers=fran_players,
                           tplayers=trans_players,
                           sfplayers=super_fran_players,
                           k2players=k2players,
                           k1players=k1players
                           )


@main.route('/reset_keepers', methods=['POST'])
@login_required
def reset_keepers():
    # get current owner
    current_owner = Owner.query.get(session.get('owner').get('id'))
    # get players that have tags or are k2s and reset
    tagged_players = Player.query.filter_by(owner=current_owner).filter(Player.tag.in_(_TAGS)).all()
    k2s = Player.query.filter_by(owner=current_owner).filter(
        and_(Player.contractStatus == "K", Player.contractYear == "2")).all()
    for p in itertools.chain(tagged_players, k2s):
        p.reset_contract_info(current_owner.mfl_team_id)
    current_owner.keeperSet = False
    db.session.commit()
    session['owner'] = current_owner.to_dict()
    return redirect(url_for('main.keepers'))


@main.route('/bidding', methods=['GET', 'POST'])
@login_required
def bidding():
    bidding_on = States.query.filter(States.name == 'biddingOn').scalar().bools
    if bidding_on:
        trans_player = Player.query.filter(Player.upForBid is True).filter(Player.tag == "TRANS").scalar()
        fran_player = Player.query.filter(Player.upForBid is True).filter(Player.tag == "FRAN").scalar()
        current_owner = Owner.query.get(session.get('owner').get('id'))
        if current_owner.madeBid:
            t_bid = Bid.query.filter(Bid.player_id == trans_player.id) \
                .filter(Bid.owner_bidding_id == current_owner.id) \
                .scalar()
            f_bid = Bid.query.filter(Bid.player_id == fran_player.id) \
                .filter(Bid.owner_bidding_id == current_owner.id) \
                .scalar()
        else:
            t_bid = None
            f_bid = None

        if request.method == 'GET':
            round1_picks = [pick.pickInRound for pick in
                            current_owner.draftPicks.filter(DraftPick.draftRound == 1).all()]
            round2_picks = [pick.pickInRound for pick in
                            current_owner.draftPicks.filter(DraftPick.draftRound == 2).all()]
            return render_template('bidding.html',
                                   transPlayer=trans_player,
                                   franPlayer=fran_player,
                                   biddingOn=bidding_on,
                                   tBid=t_bid,
                                   fBid=f_bid,
                                   madeBid=current_owner.madeBid,
                                   round1Picks=round1_picks,
                                   round2Picks=round2_picks,
                                   )

        if request.method == 'POST':
            # This is where you make a bid, set that the owner made a bid, then return stuff for the bidding page that
            # indicates the owner has made a bid on a player
            fran_player_bid = int(request.form.get('franPlayerBid') or 0)
            trans_player_bid = int(request.form.get('transPlayerBid') or 0)
            fran_bounty = request.form.get('franBounty') or None
            trans_bounty = request.form.get('transBounty') or None

            if not fran_player_bid and not trans_player_bid:
                flash("You didn't enter a bid for either player.")
                return redirect(url_for('main.bidding'))

            if trans_bounty != 'money' and trans_bounty is not None:
                trans_bounty = int(trans_bounty)
            if fran_bounty != 'money' and fran_bounty is not None:
                fran_bounty = int(fran_bounty)

            invalid_bid = False

            if 0 < fran_player_bid < 30:
                flash("Minimum bid for a Franchise Player is $30")
                invalid_bid = True

            if 0 < trans_player_bid < 20:
                flash("Minimum bid for a Transition Player is $20")
                invalid_bid = True
            if trans_player_bid > 100 or fran_player_bid > 100:
                flash("Over $100?  Really?  This isn't Brandon Jackson.  Try again...")
                invalid_bid = True

            if invalid_bid:
                return redirect(url_for('main.bidding'))
            else:
                t_bid = Bid(player_id=trans_player.id, owner_bidding_id=current_owner.id, amount=trans_player_bid,
                            bounty=trans_bounty)
                f_bid = Bid(player_id=fran_player.id, owner_bidding_id=current_owner.id, amount=fran_player_bid,
                            bounty=fran_bounty)
                db.session.add_all([t_bid, f_bid])

                current_owner.madeBid = True
                session['owner'] = current_owner.to_dict()

                db.session.commit()
                return redirect(url_for('main.bidding'))
    else:  # bidding is off.  redirect to 'matching' page, or whatever I'll call it
        # return "Bidding is off right now.  Just go back."
        return redirect(url_for('main.match'))


@main.route('/reset_bids', methods=['POST'])
@login_required
def reset_bids():
    trans_player = Player.query.filter(Player.upForBid is True).filter(Player.tag == "TRANS").scalar()
    fran_player = Player.query.filter(Player.upForBid is True).filter(Player.tag == "FRAN").scalar()
    current_owner = Owner.query.get(session.get('owner').get('id'))

    # find bid for transPlayer with current_owner, delete it
    t_bid = Bid.query.filter(Bid.player_id == trans_player.id).filter(
        Bid.owner_bidding_id == session.get('owner').get('id')).scalar()
    db.session.delete(t_bid)
    # find bid for franPlayer with current_owner, delete it
    f_bid = Bid.query.filter(Bid.player_id == fran_player.id).filter(
        Bid.owner_bidding_id == session.get('owner').get('id')).scalar()
    db.session.delete(f_bid)

    current_owner.madeBid = False
    session['owner'] = current_owner.to_dict()
    db.session.commit()
    return redirect(url_for('main.bidding'))


@main.route('/match', methods=['GET'])
@login_required
def match():
    bidding_on = States.query.filter(States.name == 'biddingOn').scalar().bools
    franchise_decision_made = States.query.filter(States.name == 'franchiseDecisionMade').scalar().bools
    transition_decision_made = States.query.filter(States.name == 'transitionDecisionMade').scalar().bools
    if bidding_on:  # make sure no one comes here on accident
        return redirect(url_for('main.bidding'))
    else:
        # get the current players up for bid
        trans_player = Player.query.filter(Player.upForBid is True).filter(Player.tag == "TRANS").scalar()
        fran_player = Player.query.filter(Player.upForBid is True).filter(Player.tag == "FRAN").scalar()

        # get the winning transition and franchise bids
        # bidding.py stop_bid() should have run, so can get winning bid via queries
        winning_trans_bid = Bid.query.filter(Bid.player_id == trans_player.id).filter(Bid.winningBid is True).scalar()
        winning_fran_bid = Bid.query.filter(Bid.player_id == fran_player.id).filter(Bid.winningBid is True).scalar()

        return render_template('match.html',
                               transPlayer=trans_player,
                               franPlayer=fran_player,
                               tBid=winning_trans_bid,
                               fBid=winning_fran_bid,
                               franchiseDecisionMade=franchise_decision_made,
                               transitionDecisionMade=transition_decision_made,
                               )


@main.route('/matchTrans', methods=['POST'])
@login_required
def match_trans():
    message = process_match_release_player("TRANS", request.form.get('transMatch'), 2)
    transition_decision_made = States.query.filter(States.name == 'transitionDecisionMade').scalar()
    transition_decision_made.bools = True
    db.session.commit()

    both_decisions = get_both_decisions()
    if both_decisions is True:
        # get start bid job and redo it so it happens now
        # startTime = datetime.datetime.today() + datetime.timedelta(minutes=2)
        # startJob = ts.get_job('STARTBID')
        # ts.set_job(startJob, startTime)

        subprocess.call(['/var/www/Calvinball/Calvinball/venv/bin/python2', '/var/www/Calvinball/Calvinball/bidding.py',
                         'start_bid'])

    if letBotPost:
        bot.post_message('general', message)
    else:
        print(message)
    return redirect(url_for('main.match'))


@main.route('/matchFran', methods=['POST'])
@login_required
def match_fran():
    message = process_match_release_player("FRAN", request.form.get('franMatch'), 1)
    franchise_decision_made = States.query.filter(States.name == 'franchiseDecisionMade').scalar()
    franchise_decision_made.bools = True
    db.session.commit()

    both_decisions = get_both_decisions()
    if both_decisions is True:
        # get start bid job and redo it so it happens now
        # startTime = datetime.datetime.today() + datetime.timedelta(minutes=2)
        # startJob = ts.get_job('STARTBID')
        # ts.set_job(startJob, startTime)

        subprocess.call(['/var/www/Calvinball/Calvinball/venv/bin/python2', '/var/www/Calvinball/Calvinball/bidding.py',
                         'start_bid'])
    if letBotPost:
        bot.post_message('general', message)
    else:
        print(message)
    return redirect(url_for('main.match'))


# should probably move this to bidding.py and then import it from there
def process_match_release_player(tag_type, decision, draft_round):
    player_up_for_bid = Player.query.filter(Player.upForBid is True).filter(Player.tag == tag_type).scalar()
    winning_bid = Bid.query.filter(Bid.player_id == player_up_for_bid.id).filter(Bid.winningBid is True).scalar()
    winning_pick = winning_bid.draftPick
    current_owner = Owner.query.get(player_up_for_bid.owner.id)
    bidding_owner = Owner.query.get(winning_bid.owner_bidding_id)

    if decision == 'match':  # keep player
        # could do lots of things... but really don't need to do anything
        message = "{0} has decided to keep {1} at a price of ${2}." \
            .format(current_owner.team_name,
                    player_up_for_bid.name,
                    winning_bid.amount
                    )
    else:  # release player
        player_up_for_bid.update_owner(bidding_owner.id)
        if winning_pick:
            DraftPick.query.filter(
                and_(DraftPick.pickInRound == winning_pick, DraftPick.draftRound == draft_round)).scalar().update_pick(
                current_owner.id)
        message = "{0} has decided to let {1} take his talents to {2}." \
            .format(current_owner.team_name,
                    player_up_for_bid.name,
                    bidding_owner.team_name)

    return message


@main.route('/draft_order', methods=['GET'])
@login_required
def draft_order():
    draft_picks = DraftPick.query.all()
    return render_template('draftOrder.html', draftPicks=draft_picks)


def get_both_decisions():
    franchise_decision_made = States.query.filter(States.name == 'franchiseDecisionMade').scalar().bools
    transition_decision_made = States.query.filter(States.name == 'transitionDecisionMade').scalar().bools
    return franchise_decision_made and transition_decision_made
