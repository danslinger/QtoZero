import os
from app.models import States, Player, Owner, Bid, DraftPick
from app import db, create_app
import random
import sys
from operator import attrgetter

def getRandomPlayer(playerType):
    # query for all players of tag==playerType whose finishedBidding is false
    players = Player.query.filter(Player.tag == playerType) \
                          .filter(Player.finishedBidding == False).all()
    if players:
        return random.choice(players)
    else: 
        return None

def startBid():
    #make sure all owners madeBid attribute is set to False
    owners = Owner.query.all()
    for o in owners:
        o.madeBid = False
    tPlayer = getRandomPlayer("TRANS")
    tPlayer.upForBid = True
    
    fPlayer = getRandomPlayer("FRAN")
    fPlayer.upForBid = True

    States.query.filter(States.name == 'biddingOn').scalar().bools = True
    db.session.commit()


    # print fPlayer, tPlayer

def stopBid():
    # get the tPlayer and fPlayer
    tPlayer = Player.query.filter(Player.tag == 'TRANS').filter(Player.upForBid == True).scalar()
    fPlayer = Player.query.filter(Player.tag == 'FRAN').filter(Player.upForBid == True).scalar()

    winningTransBid = highestBid(tPlayer, 'TRANS')
    winningFranBid = highestBid(fPlayer, 'FRAN')

    # print winningTransBid, winningFranBid

    #update the bidding state
    States.query.filter(States.name == 'biddingOn').scalar().bools = False

    #set winning bids 
    winningTransBid.winningBid = True
    winningFranBid.winningBid = True

    db.session.commit()
    


def getBids(player):
    return Bid.query.filter(Bid.player_id == player.id).all()

def highestBid(player, tagType):
    bids = getBids(player)
    highAmount = max(bids, key=attrgetter('amount')).amount
    winningBids = [b for b in bids if b.amount == highAmount]
    if len(winningBids) == 0:
        print "No winning bids"
    elif len(winningBids) == 1:
        #only one winning bid
        return winningBids[0]
    else:
        return getBidWithHighestPick(winningBids, tagType)

def getBidWithHighestPick(winningBids, tagType):
    if tagType == "FRAN":
        rd = 1
    else:
        rd = 2
    owners = [bid.owner_bidding for bid in winningBids]
    # print owners
    picksList = []
    for owner in owners:
        picksList.append(owner.draftPicks.filter(DraftPick.draftRound==rd).all())
    picks = [pick for pks in picksList for pick in pks] #flattens list
    highestPickIndex = picks.index(min(picks, key=attrgetter('pickInRound')))
    return winningBids[highestPickIndex]


if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_CONFIG') or 'default').app_context().push()
    action = sys.argv[1]

    if action == 'stopBid':  
        stopBid()

    elif action == 'startBid':
        startBid()

    

