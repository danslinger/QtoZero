import os
from app.models import States, Player, Owner, Bid, DraftPick
from app import db, create_app, login_manager
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
    # get the tPlayer and fPlayer.  None if first time - previous player bid if not
    tPlayer = Player.query.filter(Player.tag == 'TRANS').filter(Player.upForBid == True).scalar()
    fPlayer = Player.query.filter(Player.tag == 'FRAN').filter(Player.upForBid == True).scalar()
    franchiseDecisionMade = States.query.filter(States.name == 'franchiseDecisionMade').scalar().bools
    transitionDecisionMade = States.query.filter(States.name == 'transitionDecisionMade').scalar().bools

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

    owners = Owner.query.all()
    for o in owners:
        o.madeBid = False
    tPlayer = getRandomPlayer("TRANS")
    tPlayer.upForBid = True
    
    fPlayer = getRandomPlayer("FRAN")
    fPlayer.upForBid = True

    States.query.filter(States.name == 'biddingOn').scalar().bools = True
    States.query.filter(States.name == 'franchiseDecisionMade').scalar().bools = False
    States.query.filter(States.name == 'transitionDecisionMade').scalar().bools = False
    db.session.commit()

def stopBid():
    # get the tPlayer and fPlayer
    tPlayer = Player.query.filter(Player.tag == 'TRANS').filter(Player.upForBid == True).scalar()
    fPlayer = Player.query.filter(Player.tag == 'FRAN').filter(Player.upForBid == True).scalar()

    tBids = getBids(tPlayer)
    fBids = getBids(fPlayer)

    processBids(tPlayer, 'TRANS', tBids)
    processBids(fPlayer, 'FRAN', fBids)

    #update the bidding state
    States.query.filter(States.name == 'biddingOn').scalar().bools = False
    
    tPlayer.finishedBidding = True
    fPlayer.finishedBidding = True
    db.session.commit()
    
##### NEED TO FIGURE OUT OWNER in SESSION.  Force log out? ########


def getBids(player):
    allBids = Bid.query.filter(Bid.player_id == player.id).all()
    return [b for b in allBids if b.amount > 0]

def highestBid(player, tagType, bids):
    if len(bids) == 1: #There is only 1 bid
        winningBid = bids[0]
        winnningBid.winningAmount = winningBid.amount
    else:
        #need to find the highest bid, then modify it so it is the second highest bid + 1
        #unless the second highest == highest, then it is just the highest
    
        highAmount = max(bids, key=attrgetter('amount')).amount

        # allBidAmounts = [b.amount for b in bids]
        # highBidCount = allBidAmounts.count(highAmount)
        # high bid amount is the amount.  No second highest + 1
        winningBids = [b for b in bids if b.amount == highAmount]
        winningBid = getBidWithHighestPick(winningBids, tagType)  
        
                # OLD cases to handle are: single high bid, multiple high bid
        
                # if highBidCount == 1: #single high bid
                #     allBidAmounts.remove(highAmount)
                #     secondHighAmount = max(allBidAmounts)
                #     winningBid = next(b for b in bids if b.amount == highAmount)
                #     winningBid.winningAmount = secondHighAmount + 1
                # else: #multiple high bid
                #     winningBids = [b for b in bids if b.amount )== highAmount]
        #     winningBid = getBidWithHighestPick(winningBids, tagType)
        #     winningBid.winningAmount = highAmount

        db.session.commit()
    return winningBid

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

def processBids(player,tag, bids):
    if bids:
        winningBid = highestBid(player, tag, bids)
        winningBid.winningBid = True
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
        db.session.add(winningBid)
    db.session.commit()


if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_CONFIG') or 'default').app_context().push()
    action = sys.argv[1]

    if action == 'stopBid':  
        stopBid()

    elif action == 'startBid':
        startBid()

    

