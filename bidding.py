import datetime
import os
import random
import sys
from operator import attrgetter

from sqlalchemy import and_, true

from SlackBot import SlackBot
from TaskScheduler import TaskScheduler
from app import db, create_app
from app.models.owner import Owner
from app.models.player import Player
from app.models.draft_pick import DraftPick
from app.models.bid import Bid
from app.models.states import States
from local_settings import let_bot_post

bot = SlackBot()
ts = TaskScheduler()
timeFormatString = '%A %B %d at %I:%M%p'
letBotPost = let_bot_post
# pylint: disable=singleton-comparison


def get_random_player(player_type):
    # query for all players of tag==playerType whose finishedBidding is false
    players = Player.query.filter(Player.tag == player_type) \
        .filter(Player.finishedBidding is False).all()
    if players:
        return random.choice(players)
    else:
        return None


def get_next_player(player_type, playerIndex):
    return get_next_fran(playerIndex) if player_type == "FRAN" else get_next_tran(playerIndex)


def get_next_fran(playerIndex):
    # These were called out specifically because we were announcing the draft order
    # Should really write a function that does the randomness, then stores the order in
    # its own table.  Then get_next_player can take the tag type and get the next
    # player from that table.
    fps = [
        Player.query.get(33),
        Player.query.get(77),
        Player.query.get(144),
        Player.query.get(163),
        Player.query.get(197)
    ]

    return fps[playerIndex] if playerIndex < len(fps) else None


def get_next_tran(playerIndex):
    tps = [
        Player.query.get(1),
        Player.query.get(25),
        Player.query.get(40),
        Player.query.get(64),
        Player.query.get(75),
        Player.query.get(114),
        Player.query.get(129),
        Player.query.get(148),
        Player.query.get(172),
    ]
    if playerIndex < len(tps):
        return tps[playerIndex]
    else:
        return None


def cleanup_previous_round():
    message = ''
    franchise_decision_made = States.query.filter(
        States.name == 'franchiseDecisionMade').first().bools
    transition_decision_made = States.query.filter(
        States.name == 'transitionDecisionMade').first().bools
    # get the t_player and f_player.  None if first time - previous player bid if not
    t_player = Player.query.filter(Player.tag == 'TRANS').filter(
        Player.upForBid == true()).first()
    f_player = Player.query.filter(Player.tag == 'FRAN').filter(
        Player.upForBid == true()).first()

    if t_player:  # not the first time
        # if owner of transition pick didn't make a decision, the player changes hands
        if not transition_decision_made:
            message += process_match_release_player("TRANS", "release", 2)
        t_player.upForBid = False
    if f_player:  # not the first time
        # if owner of franchise pick didn't make a decision, the player changes hands
        if not franchise_decision_made:
            message += process_match_release_player("FRAN", "release", 1)
        f_player.upForBid = False
    return message


def start_bid():
    message = ''
    biddingState = States.query.filter_by(name="biddingOn").first()
    if Player.query.filter(Player.upForBid == true()).count() == 0 and biddingState.bools is False:
        biddingState.number = 0
    else:
        biddingState.number = biddingState.number + 1

    franchise_decision_made = States.query.filter(
        States.name == 'franchiseDecisionMade').scalar().bools
    transition_decision_made = States.query.filter(
        States.name == 'transitionDecisionMade').scalar().bools

    message = cleanup_previous_round()

    # make sure all owners madeBid attribute is set to False
    owners = Owner.query.all()
    for o in owners:
        o.madeBid = False

    t_player = get_next_player("TRANS", biddingState.number)
    if t_player:
        t_player.upForBid = True
        transition_decision_made = False
        message += 'The transition player now up for bid is {0}.\n'.format(t_player.name)
    else:
        message += 'There are no transition players up for bid.\n'

    f_player = get_next_player("FRAN", biddingState.number)
    if f_player:
        f_player.upForBid = True
        franchise_decision_made.bools = False
        message += 'The franchise player now up for bid is {0}.\n'.format(f_player.name)
    else:
        message += 'There are no franchise players up for bid.\n'

    biddingState.bools = True

    print(f_player, t_player)
    db.session.commit()
    # Reset Cron job time

    stop_time = datetime.datetime.today() + datetime.timedelta(hours=48)
    command = get_bidding_command("stop_bid")
    stop_job = ts.get_job("STOPBID", command)
    ts.set_job(stop_job, stop_time)
    message += 'Bidding for these players ends '
    message += stop_time.strftime(timeFormatString)

    # Post Bot Message
    if letBotPost:
        bot.post_message(message, 'general_url')
    else:
        print(message)


def get_bidding_command(arg):
    pwd = os.getcwd()
    program = os.path.join(pwd, "Calvinball/venv/bin/python")
    script_to_run = os.path.join(pwd, "Calvinball/bidding.py")
    command = f"{program} {script_to_run} {arg} "
    return command


def stop_bid():
    # get the t_player and f_player
    t_player = Player.query.filter(Player.tag == 'TRANS').filter(
        Player.upForBid == true()).scalar()
    f_player = Player.query.filter(Player.tag == 'FRAN').filter(
        Player.upForBid == true()).scalar()

    t_bids = get_bids(t_player)
    f_bids = get_bids(f_player)

    if t_bids:
        was_no_trans_bid = process_bids(t_player, 'TRANS', t_bids) or False
    else:
        was_no_trans_bid = True
    if f_bids:
        was__no_fran_bid = process_bids(f_player, 'FRAN', f_bids) or False
    else:
        was__no_fran_bid = True

    # update the bidding state
    States.query.filter(States.name == 'biddingOn').scalar().bools = False

    if t_player:
        t_player.finishedBidding = True
    if f_player:
        f_player.finishedBidding = True
    db.session.commit()

    if was__no_fran_bid and was_no_trans_bid:
        message = "There were no bids made this round on any player."
        start_time = datetime.datetime.today() + datetime.timedelta(minutes=1)
        command = get_bidding_command("start_bid")
        start_job = ts.get_job('STARTBID', command)
        ts.set_job(start_job, start_time)

    else:
        # Set STARTBID to 24 hours later
        start_time = datetime.datetime.today() + datetime.timedelta(hours=24)
        command = get_bidding_command("start_bid")
        start_job = ts.get_job('STARTBID', command)
        ts.set_job(start_job, start_time)
        message = "Owners must match or release by {0}.  New players will be available to pick " \
                  "at that time".format(start_time.strftime(timeFormatString))
        message += "  If both are matched or released before then, new players will be available" \
                   " at that time"
        message += "  I'll send a message when new players are available."

    if letBotPost:
        bot.post_message(message, 'general_url')
    else:
        print(message)


# NEED TO FIGURE OUT OWNER in SESSION.  Force log out? ########


def get_bids(player):
    if player:
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
    ''' This processes the bids at stop bid time'''
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
            bounty_string = "Pick {0} in the {1} round".format(
                winning_bid.draftPick, 'first' if tag == "FRAN" else "second")

        message += "{0} has the highest bid on {1} at ${2} and will give up {3} " \
            "if the bid is not matched" \
            .format(Owner.query.get(winning_bid.owner_bidding_id).team_name,
                    player.name,
                    winning_bid.amount,
                    bounty_string
                    )
        was_no_bids = False
    else:
        if tag == 'TRANS':
            amount = 20
            States.query.filter(
                States.name == 'transitionDecisionMade').scalar().bools = True

        elif tag == 'FRAN':
            amount = 30
            States.query.filter(
                States.name == 'franchiseDecisionMade').scalar().bools = True

        winning_bid = Bid(
            player_id=player.id,
            owner_bidding_id=player.owner.id,
            amount=amount,
        )
        winning_bid.winningBid = True
        message = "No one bid on {0}. He is staying put.".format(player.name)
        was_no_bids = True
        db.session.add(winning_bid)
    db.session.commit()
    if letBotPost:
        bot.post_message(message, 'general_url')
    else:
        print(message)
    return was_no_bids


# copied from views.py - should really just be in one place
def process_match_release_player(tag_type, decision, draft_round):
    ''' This processes the matching/releasing of players if the time limit was up and 
    the previous owner didn't make a choice.'''
    player_up_for_bid = Player.query.filter(Player.upForBid == true()).filter(
        Player.tag == tag_type).scalar()
    winning_bid = Bid.query.filter(
        Bid.player_id == player_up_for_bid.id).filter(
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
                and_(
                    DraftPick.pickInRound == winning_pick,
                    DraftPick.draftRound == draft_round)).scalar().update_pick(
                        current_owner.id)
        message = "{0} has decided to let {1} take his talents to {2}." \
            .format(current_owner.team_name,
                    player_up_for_bid.name,
                    bidding_owner.team_name)
    message += "\n"
    return message


if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_CONFIG')
                     or 'default').app_context().push()
    action = sys.argv[1]

    if action == 'stop_bid':
        stop_bid()

    elif action == 'start_bid':
        start_bid()
