import os
import subprocess
from flask import render_template, redirect, request, url_for, flash, session
from flask_login import login_required
from sqlalchemy.sql.expression import and_, true

from app.models.owner import Owner
from app.models.player import Player
from app.models.states import States
from app.models.bid import Bid
from app.models.draft_pick import DraftPick
from SlackBot import SlackBot
from local_settings import let_bot_post
from . import main
from .. import db

bot = SlackBot()

# pylint: disable=singleton-comparison


@main.route('/bidding', methods=['GET', 'POST'])
@login_required
def bidding():
    bidding_on_state = States.query.filter(States.name == 'biddingOn').scalar()
    bidding_on = bidding_on_state.bools if bidding_on_state else False
    if bidding_on:
        trans_player = Player.query.filter(
            Player.upForBid == true()).filter(Player.tag == "TRANS").scalar()
        fran_player = Player.query.filter(
            Player.upForBid == true()).filter(Player.tag == "FRAN").scalar()
        current_owner = Owner.query.get(session.get('owner').get('id'))
        if current_owner.madeBid:
            if trans_player is not None:
                t_bid = Bid.query.filter(Bid.player_id == trans_player.id) \
                    .filter(Bid.owner_bidding_id == current_owner.id) \
                    .scalar()
            else:
                t_bid = None
            if fran_player is not None:
                f_bid = Bid.query.filter(Bid.player_id == fran_player.id) \
                    .filter(Bid.owner_bidding_id == current_owner.id) \
                    .scalar()
            else:
                f_bid = None
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
            # This is where you make a bid, set that the owner made a bid,
            # then return stuff for the bidding page that
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
                if trans_player is not None:
                    t_bid = Bid(player_id=trans_player.id,
                                owner_bidding_id=current_owner.id,
                                amount=trans_player_bid,
                                bounty=trans_bounty)
                    db.session.add(t_bid)
                if fran_player is not None:
                    f_bid = Bid(player_id=fran_player.id,
                                owner_bidding_id=current_owner.id,
                                amount=fran_player_bid,
                                bounty=fran_bounty)
                    db.session.add(f_bid)

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
    trans_player = Player.query.filter(
        Player.upForBid == true()).filter(Player.tag == "TRANS").scalar()
    fran_player = Player.query.filter(
        Player.upForBid == true()).filter(Player.tag == "FRAN").scalar()
    current_owner = Owner.query.get(session.get('owner').get('id'))

    # find bid for transPlayer with current_owner, delete it
    if trans_player:
        t_bid = Bid.query.filter(Bid.player_id == trans_player.id).filter(
            Bid.owner_bidding_id == session.get('owner').get('id')).scalar()
        db.session.delete(t_bid)
    # find bid for franPlayer with current_owner, delete it
    if fran_player:
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
    franchise_decision_made = States.query.filter(
        States.name == 'franchiseDecisionMade').scalar().bools
    transition_decision_made = States.query.filter(
        States.name == 'transitionDecisionMade').scalar().bools
    if bidding_on:  # make sure no one comes here on accident
        return redirect(url_for('main.bidding'))
    else:
        # get the current players up for bid
        trans_player = Player.query.filter(
            Player.upForBid == true()).filter(Player.tag == "TRANS").scalar()
        fran_player = Player.query.filter(
            Player.upForBid == true()).filter(Player.tag == "FRAN").scalar()

        # get the winning transition and franchise bids
        # bidding.py stop_bid() should have run, so can get winning bid via queries
        winning_trans_bid = Bid.query.filter(
            Bid.player_id == trans_player.id).filter(Bid.winningBid == true()).scalar()
        winning_fran_bid = Bid.query.filter(
            Bid.player_id == fran_player.id).filter(Bid.winningBid == true()).scalar()

        return render_template('match.html',
                               transPlayer=trans_player,
                               franPlayer=fran_player,
                               tBid=winning_trans_bid,
                               fBid=winning_fran_bid,
                               franchiseDecisionMade=franchise_decision_made,
                               transitionDecisionMade=transition_decision_made,
                               )


@main.route('/match_trans', methods=['POST'])
@login_required
def match_trans():
    message = process_match_release_player(
        "TRANS", request.form.get('transMatch'), 2)
    transition_decision_made = States.query.filter(
        States.name == 'transitionDecisionMade').scalar()
    transition_decision_made.bools = True
    db.session.commit()

    both_decisions = get_both_decisions()
    if both_decisions is True:
        # get start bid job and redo it so it happens now
        # startTime = datetime.datetime.today() + datetime.timedelta(minutes=2)
        # startJob = ts.get_job('STARTBID')
        # ts.set_job(startJob, startTime)
        pwd = os.getcwd()
        subprocess.call([os.path.join(pwd, 'venv/bin/python'), os.path.join(pwd, 'bidding.py'),
                         'start_bid'])

    if let_bot_post:
        bot.post_message(message, 'general_url')
    else:
        print(message)
    return redirect(url_for('main.match'))


@main.route('/match_fran', methods=['POST'])
@login_required
def match_fran():
    message = process_match_release_player(
        "FRAN", request.form.get('franMatch'), 1)
    franchise_decision_made = States.query.filter(
        States.name == 'franchiseDecisionMade').scalar()
    franchise_decision_made.bools = True
    db.session.commit()

    both_decisions = get_both_decisions()
    if both_decisions is True:
        # get start bid job and redo it so it happens now
        # startTime = datetime.datetime.today() + datetime.timedelta(minutes=2)
        # startJob = ts.get_job('STARTBID')
        # ts.set_job(startJob, startTime)
        pwd = os.getcwd()
        subprocess.call([os.path.join(pwd, 'venv/bin/python'), os.path.join(pwd, 'bidding.py'),
                         'start_bid'])
    if let_bot_post:
        bot.post_message(message, 'general_url')
    else:
        print(message)
    return redirect(url_for('main.match'))


# should probably move this to bidding.py and then import it from there
def process_match_release_player(tag_type, decision, draft_round):
    player_up_for_bid = Player.query.filter(
        Player.upForBid == true()).filter(Player.tag == tag_type).scalar()
    winning_bid = Bid.query.filter(Bid.player_id == player_up_for_bid.id).filter(
        Bid.winningBid == true()).scalar()
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
        player_up_for_bid.owner = bidding_owner.id
        if winning_pick:
            DraftPick.query.filter(
                and_(DraftPick.pickInRound == winning_pick,
                     DraftPick.draftRound == draft_round)
            ).scalar().update_pick(current_owner.id)
        message = "{0} has decided to let {1} take his talents to {2}." \
            .format(current_owner.team_name,
                    player_up_for_bid.name,
                    bidding_owner.team_name)

    return message


def get_both_decisions():
    franchise_decision_made = States.query.filter(
        States.name == 'franchiseDecisionMade').scalar().bools
    transition_decision_made = States.query.filter(
        States.name == 'transitionDecisionMade').scalar().bools
    return franchise_decision_made and transition_decision_made
