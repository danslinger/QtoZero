import os
from app.models import States, Player, Owner, Bid, DraftPick
from app import db, create_app, login_manager
import random
import sys
from operator import attrgetter
from SlackBot import SlackBot
from TaskScheduler import TaskScheduler
import datetime

bot = SlackBot()
ts = TaskScheduler()
timeFormatString = '%A %B %d at %I:%M%p'
letBotPost = True

def getRandomPlayer(playerType):
    # query for all players of tag==playerType whose finishedBidding is false
    players = Player.query.filter(Player.tag == playerType) \
                          .filter(Player.finishedBidding == False).all()
    if players:
        return random.choice(players)
    else: 
        return None

def startBid():
    # get the tPlayer and fPlayer.  None if first time - previous player bid if not
    tPlayer = Player.query.filter(Player.tag == 'TRANS').filter(Player.upForBid == True).scalar()
    fPlayer = Player.query.filter(Player.tag == 'FRAN').filter(Player.upForBid == True).scalar()
    franchiseDecisionMade = States.query.filter(States.name == 'franchiseDecisionMade').scalar().bools
    transitionDecisionMade = States.query.filter(States.name == 'transitionDecisionMade').scalar().bools

    print "Starting Bid"
    if tPlayer: #not the first time
        # if owner of transition pick didn't make a decision, the player changes hands
        if not transitionDecisionMade:
            winningTransBid = Bid.query.filter(Bid.player_id == tPlayer.id).filter(Bid.winningBid == True).scalar()
            winningTransPicks = winningTransBid.owner_bidding.draftPicks.filter(DraftPick.draftRound==2).all()
            highestTransPick = min(winningTransPicks, key=attrgetter('pickInRound'))
            current_owner = Owner.query.get(tPlayer.owner.id)
            bidding_owner = Owner.query.get(highestTransPick.owner_id)
            tPlayer.updateOwner(bidding_owner.id)
            highestTransPick.updatePick(current_owner.id)
        tPlayer.upForBid = False
    if fPlayer: #not the first time
        # if owner of franchise pick didn't make a decision, the player changes hands
        if not franchiseDecisionMade:
            winningFranBid = Bid.query.filter(Bid.player_id == fPlayer.id).filter(Bid.winningBid == True).scalar()
            winningFranPicks = winningFranBid.owner_bidding.draftPicks.filter(DraftPick.draftRound==1).all()
            highestFranPick = min(winningFranPicks, key=attrgetter('pickInRound'))
            current_owner = Owner.query.get(fPlayer.owner.id)
            bidding_owner = Owner.query.get(highestFranPick.owner_id)
            fPlayer.updateOwner(bidding_owner.id)
            highestFranPick.updatePick(current_owner.id)
        fPlayer.upForBid = False

    #make sure all owners madeBid attribute is set to False
    owners = Owner.query.all()
    for o in owners:
        o.madeBid = False
    message = ''

    print "Getting Trans"
    tPlayer = getRandomPlayer("TRANS")
    if tPlayer:
        tPlayer.upForBid = True
        States.query.filter(States.name == 'transitionDecisionMade').scalar().bools = False
        message += 'The transition player now up for bid is {0}.\n'.format(tPlayer.name)
    else:
        message += 'There are no transition players up for bid.\n'        

    print "Getting FRAN"
    
    fPlayer = getRandomPlayer("FRAN")
    if fPlayer:
        fPlayer.upForBid = True
        States.query.filter(States.name == 'franchiseDecisionMade').scalar().bools = False
        message += 'The franchise player now up for bid is {0}.\n'.format(fPlayer.name)
    else:
        message += 'There are no franchise players up for bid.\n'

    States.query.filter(States.name == 'biddingOn').scalar().bools = True

    print fPlayer, tPlayer
    db.session.commit()
    # Reset Cron job time
    
    stopTime = datetime.datetime.today() + datetime.timedelta(hours=48)
    stopJob = ts.getJob("STOPBID")
    ts.setJob(stopJob, stopTime)
    message += 'Bidding for these players ends '
    message += stopTime.strftime(timeFormatString)

    #Post Bot Message
    if letBotPost:
        bot.postMessage('general', message)
    else:
        print message


def stopBid():
    # get the tPlayer and fPlayer
    tPlayer = Player.query.filter(Player.tag == 'TRANS').filter(Player.upForBid == True).scalar()
    fPlayer = Player.query.filter(Player.tag == 'FRAN').filter(Player.upForBid == True).scalar()

    tBids = getBids(tPlayer)
    fBids = getBids(fPlayer)

    was_no_trans_bid = processBids(tPlayer, 'TRANS', tBids)
    was__no_fran_bid = processBids(fPlayer, 'FRAN', fBids)

    #update the bidding state
    States.query.filter(States.name == 'biddingOn').scalar().bools = False
    
    tPlayer.finishedBidding = True
    fPlayer.finishedBidding = True
    db.session.commit()

    if was__no_fran_bid and was_no_trans_bid:
        message = "There were no bids made this round on any player."
        startTime = datetime.datetime.today() + datetime.timedelta(minutes=1)
        startJob = ts.getJob('STARTBID')
        ts.setJob(startJob, startTime)

    else:
        # Set STARTBID to 24 hours later
        startTime = datetime.datetime.today() + datetime.timedelta(hours=24)
        startJob = ts.getJob('STARTBID')
        ts.setJob(startJob, startTime)
        message = "Owners must match or release by {0}.  New players will be available to pick at that time".format(startTime.strftime(timeFormatString))
        message += "  If both are matched or released before then, new players will be available at that time"
        message += "  I'll send a message when new players are available."
    
    if letBotPost:
        bot.postMessage('general', message)
    else:
        print message


    
##### NEED TO FIGURE OUT OWNER in SESSION.  Force log out? ########


def getBids(player):
    allBids = Bid.query.filter(Bid.player_id == player.id).all()
    return [b for b in allBids if b.amount > 0]

def highestBid(player, tagType, bids):
    if len(bids) == 1: #There is only 1 bid
        winningBid = bids[0]
        winningBid.winningAmount = winningBid.amount
    else:
        highAmount = max(bids, key=attrgetter('amount')).amount
        winningBids = [b for b in bids if b.amount == highAmount]
        winningBid = getBidWithHighestPick(winningBids, tagType)  
        
        db.session.commit()
    return winningBid

def getBidWithHighestPick(winningBids, tagType):
    highestDraftPick = min(winningBids, key=attrgetter('draftPick')) or None
    if highestDraftPick is None:
        return winningBids[0] #For now, just whoever put their bid in first
    else:
        return winningBids[winningBids.index(highestDraftPick)]
    
    # Old way
    # if tagType == "FRAN":
    #     rd = 1
    # else:
    #     rd = 2
    # owners = [bid.owner_bidding for bid in winningBids]
    # picksList = []
    # for owner in owners:
    #     picksList.append(owner.draftPicks.filter(DraftPick.draftRound==rd).all())
    # picks = [pick for pks in picksList for pick in pks] #flattens list
    # highestPickIndex = picks.index(min(picks, key=attrgetter('pickInRound')))
    # return winningBids[highestPickIndex]

def processBids(player,tag, bids):
    message = ''
    if bids:
        winningBid = highestBid(player, tag, bids)
        winningBid.winningBid = True
        if winningBid.bounty is True:
            if tag == 'TRANS':
                bountyString = "$15 FAAB"
            else:
                bountyString = "$10 CAB"
        else:
            bountyString = "Pick {0} in the {1} round".format(winningBid.draftPick, "first" if tag == "FRAN" else "second")

        message += "{0} has the highest bid on {1} at ${2} and will give up {3} if the bid is not matched"\
                                                                  .format(Owner.query.get(winningBid.owner_bidding_id).team_name,
                                                                   player.name,
                                                                   winningBid.amount,
                                                                   bountyString
                                                                   )
        was_no_bids = False
    else:
        if tag == 'TRANS':
            amount = 20
            States.query.filter(States.name == 'transitionDecisionMade').scalar().bools = True
            
        elif tag == 'FRAN':
            amount = 30
            States.query.filter(States.name == 'franchiseDecisionMade').scalar().bools = True

        winningBid = Bid(player_id=player.id,
                         owner_bidding_id = player.owner.id,
                         amount=amount,
                         )
        winningBid.winningBid = True
        message = "No one bid on {0}. He is staying put.".format(player.name)
        was_no_bids = True
        db.session.add(winningBid)
    db.session.commit()
    if letBotPost:
        bot.postMessage('general', message)
    else:
        print message
    return was_no_bids


if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_CONFIG') or 'default').app_context().push()
    action = sys.argv[1]

    if action == 'stopBid':  
        stopBid()

    elif action == 'startBid':
        startBid()

    

