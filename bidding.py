import datetime
import os
import random
import sys
from operator import attrgetter

from SlackBot import SlackBot
from TaskScheduler import TaskScheduler
from app import db, create_app
from app.models import States, Player, Owner, Bid, DraftPick
from local_settings import let_bot_post

bot = SlackBot()
ts = TaskScheduler()
timeFormatString = '%A %B %d at %I:%M%p'
letBotPost = let_bot_post


def get_random_player(player_type):
    # query for all players of tag==playerType whose finishedBidding is false
    players = Player.query.filter(Player.tag == player_type) \
        .filter(Player.finishedBidding is False).all()
    if players:
        return random.choice(players)
    else:
        return None


# noinspection SpellCheckingInspection
def start_bid():
    # get the t_player and f_player.  None if first time - previous player bid if not
    t_player = Player.query.filter(Player.tag == 'TRANS').filter(Player.upForBid is True).scalar()
    f_player = Player.query.filter(Player.tag == 'FRAN').filter(Player.upForBid is True).scalar()
    franchise_decision_made = States.query.filter(States.name == 'franchiseDecisionMade').scalar().bools
    transition_decision_made = States.query.filter(States.name == 'transitionDecisionMade').scalar().bools

    if t_player:  # not the first time
        # if owner of transition pick didn't make a decision, the player changes hands
        if not transition_decision_made:
            winning_trans_bid = Bid.query.filter(Bid.player_id == t_player.id).filter(Bid.winningBid is True).scalar()
            winning_trans_picks = winning_trans_bid.owner_bidding.draftPicks.filter(DraftPick.draftRound == 2).all()
            highest_trans_pick = min(winning_trans_picks, key=attrgetter('pickInRound'))
            current_owner = Owner.query.get(t_player.owner.id)
            bidding_owner = Owner.query.get(highest_trans_pick.owner_id)
            t_player.update_owner(bidding_owner.id)
            highest_trans_pick.updatePick(current_owner.id)
        t_player.upForBid = False
    if f_player:  # not the first time
        # if owner of franchise pick didn't make a decision, the player changes hands
        if not franchise_decision_made:
            winning_fran_bid = Bid.query.filter(Bid.player_id == f_player.id).filter(Bid.winningBid is True).scalar()
            winning_fran_picks = winning_fran_bid.owner_bidding.draftPicks.filter(DraftPick.draftRound == 1).all()
            highest_fran_pick = min(winning_fran_picks, key=attrgetter('pickInRound'))
            current_owner = Owner.query.get(f_player.owner.id)
            bidding_owner = Owner.query.get(highest_fran_pick.owner_id)
            f_player.update_owner(bidding_owner.id)
            highest_fran_pick.updatePick(current_owner.id)
        f_player.upForBid = False

    # make sure all owners madeBid attribute is set to False
    owners = Owner.query.all()
    for o in owners:
        o.madeBid = False
    message = ''

    t_player = get_random_player("TRANS")
    if t_player:
        t_player.upForBid = True
        States.query.filter(States.name == 'transitionDecisionMade').scalar().bools = False
        message += 'The transition player now up for bid is {0}.\n'.format(t_player.name)
    else:
        message += 'There are no transition players up for bid.\n'

    f_player = get_random_player("FRAN")
    if f_player:
        f_player.upForBid = True
        States.query.filter(States.name == 'franchiseDecisionMade').scalar().bools = False
        message += 'The franchise player now up for bid is {0}.\n'.format(f_player.name)
    else:
        message += 'There are no franchise players up for bid.\n'

    States.query.filter(States.name == 'biddingOn').scalar().bools = True

    print(f_player, t_player)
    db.session.commit()
    # Reset Cron job time

    stop_time = datetime.datetime.today() + datetime.timedelta(hours=48)
    stop_job = ts.get_job("STOPBID")
    ts.set_job(stop_job, stop_time)
    message += 'Bidding for these players ends '
    message += stop_time.strftime(timeFormatString)

    # Post Bot Message
    if letBotPost:
        bot.post_message('general', message)
    else:
        print(message)


def stop_bid():
    # get the t_player and f_player
    t_player = Player.query.filter(Player.tag == 'TRANS').filter(Player.upForBid is True).scalar()
    f_player = Player.query.filter(Player.tag == 'FRAN').filter(Player.upForBid is True).scalar()

    t_bids = get_bids(t_player)
    f_bids = get_bids(f_player)

    was_no_trans_bid = process_bids(t_player, 'TRANS', t_bids)
    was__no_fran_bid = process_bids(f_player, 'FRAN', f_bids)

    # update the bidding state
    States.query.filter(States.name == 'biddingOn').scalar().bools = False

    t_player.finishedBidding = True
    f_player.finishedBidding = True
    db.session.commit()

    if was__no_fran_bid and was_no_trans_bid:
        message = "There were no bids made this round on any player."
        start_time = datetime.datetime.today() + datetime.timedelta(minutes=1)
        start_job = ts.get_job('STARTBID')
        ts.set_job(start_job, start_time)

    else:
        # Set STARTBID to 24 hours later
        start_time = datetime.datetime.today() + datetime.timedelta(hours=24)
        start_job = ts.get_job('STARTBID')
        ts.set_job(start_job, start_time)
        message = "Owners must match or release by {0}.  New players will be available to pick at that time".format(
            start_time.strftime(timeFormatString))
        message += "  If both are matched or released before then, new players will be available at that time"
        message += "  I'll send a message when new players are available."

    if letBotPost:
        bot.post_message('general', message)
    else:
        print(message)


# NEED TO FIGURE OUT OWNER in SESSION.  Force log out? ########


def get_bids(player):
    all_bids = Bid.query.filter(Bid.player_id == player.id).all()
    return [b for b in all_bids if b.amount > 0]


def highest_bid(bids):
    if len(bids) == 1:  # There is only 1 bid
        winning_bid = bids[0]
        winning_bid.winningAmount = winning_bid.amount
    else:
        high_amount = max(bids, key=attrgetter('amount')).amount
        winning_bids = [b for b in bids if b.amount == high_amount]
        winning_bid = get_bid_with_highest_pick(winning_bids)

    db.session.commit()
    return winning_bid


def get_bid_with_highest_pick(winning_bids):
    highest_draft_pick = min(winning_bids, key=attrgetter('draftPick')) or None
    if highest_draft_pick is None:
        return winning_bids[0]  # For now, just whoever put their bid in first
    else:
        return winning_bids[winning_bids.index(highest_draft_pick)]


# noinspection PyUnboundLocalVariable
def process_bids(player, tag, bids):
    message = ''
    if bids:
        winning_bid = highest_bid(bids)
        winning_bid.winningBid = True
        if winning_bid.bounty is True:
            if tag == 'TRANS':
                bounty_string = "$15 FAAB"
            else:
                bounty_string = "$10 CAB"
        else:
            bounty_string = "Pick {0} in the {1} round".format(winning_bid.draftPick,
                                                               'first' if tag == "FRAN" else "second")

        message += "{0} has the highest bid on {1} at ${2} and will give up {3} if the bid is not matched" \
            .format(Owner.query.get(winning_bid.owner_bidding_id).team_name,
                    player.name,
                    winning_bid.amount,
                    bounty_string
                    )
        was_no_bids = False
    else:
        if tag == 'TRANS':
            amount = 20
            States.query.filter(States.name == 'transitionDecisionMade').scalar().bools = True

        elif tag == 'FRAN':
            amount = 30
            States.query.filter(States.name == 'franchiseDecisionMade').scalar().bools = True

        winning_bid = Bid(player_id=player.id,
                          owner_bidding_id=player.owner.id,
                          amount=amount,
                          )
        winning_bid.winningBid = True
        message = "No one bid on {0}. He is staying put.".format(player.name)
        was_no_bids = True
        db.session.add(winning_bid)
    db.session.commit()
    if letBotPost:
        bot.post_message('general', message)
    else:
        print(message)
    return was_no_bids


if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_CONFIG') or 'default').app_context().push()
    action = sys.argv[1]

    if action == 'stop_bid':
        stop_bid()

    elif action == 'start_bid':
        start_bid()
