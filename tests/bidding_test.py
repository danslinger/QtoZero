import unittest
import os
import shutil
import itertools
import bidding
from app import db, create_app
from app.models.player import Player
from app.models.bid import Bid
from app.models.owner import Owner
from app.models.states import States
from app.models.draft_pick import DraftPick


class BiddingTests(unittest.TestCase):

    def create_database(self):
        db_path = os.getcwd()
        source = os.path.join(db_path, "data-test-oracle.sqlite")
        self.test_database = os.path.join(db_path, "data-test.sqlite")
        shutil.copyfile(source, self.test_database)

    @classmethod
    def setUpClass(self):
        self.create_database(self)

    @classmethod
    def tearDownClass(self):
        os.remove(self.test_database)

    def test_get_fran(self):
        with(create_app('testing').app_context()):
            fps = [
                Player.query.get(33),
                Player.query.get(77),
                Player.query.get(144),
                Player.query.get(163),
                Player.query.get(197)
            ]
            for i in range(0, len(fps)):
                player = bidding.get_next_fran(i)
                self.assertEqual(player, fps[i])
            player = bidding.get_next_fran(len(fps)+1)
            self.assertEqual(player, None)

    def test_get_tran(self):
        with(create_app('testing').app_context()):
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
            for i in range(0, len(tps)):
                player = bidding.get_next_tran(i)
                self.assertEqual(player, tps[i])
            player = bidding.get_next_tran(len(tps)+1)
            self.assertEqual(player, None)

    def test_highest_bid(self):
        with(create_app('testing').app_context()):
            player = Player.query.get(1)  # Carson is a trans player
            player.UpForBid = True
            danny = Owner.query.filter_by(name="Danny Anslinger").one()
            shaun = Owner.query.filter_by(name="Shaun Anderson").one()
            craig = Owner.query.filter_by(name="Craig Pearce").one()

            bid1 = Bid(player.id, danny.id, 30)
            bid2 = Bid(player.id, shaun.id, 35, 21)
            bid3 = Bid(player.id, craig.id, 40, 20)
            bids = [bid1, bid2, bid3]

            winning_bid = bidding.highest_bid(bids)
            self.assertEqual(bid3, winning_bid)

            bid1 = Bid(player.id, danny.id, 30, "money")
            bid2 = Bid(player.id, shaun.id, 30, 19)
            bid3 = Bid(player.id, craig.id, 30, 20)
            bids = [bid1, bid2, bid3]

            winning_bid = bidding.highest_bid(bids)
            self.assertEqual(bid2, winning_bid)
            # no one has pics, so it should be the first one
            bid1 = Bid(player.id, danny.id, 30, "money")
            bid2 = Bid(player.id, shaun.id, 30, "money")
            bid3 = Bid(player.id, craig.id, 30, "money")
            bids = [bid1, bid2, bid3]

            winning_bid = bidding.highest_bid(bids)
            self.assertEqual(bid1, winning_bid)

    def test_first_start_bid(self):
        with(create_app('testing').app_context()):
            danny = Owner.query.filter_by(name="Danny Anslinger").one()
            shaun = Owner.query.filter_by(name="Shaun Anderson").one()
            craig = Owner.query.filter_by(name="Craig Pearce").one()

            fran = Player.query.filter_by(contractStatus="FRAN").all()
            trans = Player.query.filter_by(contractStatus="TRANS").all()
            states = States.query.all()
            for player in itertools.chain(trans, fran):
                self.assertFalse(player.upForBid)
            for s in states:
                self.assertFalse(s.bools)
            # rd 1
            bidding.start_bid()
            carson = Player.query.get(1)
            ty = Player.query.get(33)
            gordon = Player.query.get(25)
            mixon = Player.query.get(77)
            self.assertTrue(carson.upForBid)
            self.assertTrue(ty.upForBid)
            self.assertFalse(gordon.upForBid)
            self.assertFalse(mixon.upForBid)

            # confirm states
            bidState = States.query.filter_by(name="biddingOn").first()
            fdm = States.query.filter_by(name="franchiseDecisionMade").first()
            tdm = States.query.filter_by(name="transitionDecisionMade").first()
            self.assertTrue(bidState.bools)
            self.assertFalse(fdm.bools)
            self.assertFalse(fdm.bools)
            bids = Bid.query.all()
            self.assertFalse(bids)
            self.assertTrue(len(Bid.query.filter_by(player_id=1).all()) == 0)
            self.assertTrue(len(Bid.query.filter_by(player_id=33).all()) == 0)

            # setup prior to stop bidding
            carson_owner = carson.owner
            ty_owner = ty.owner

            bidding.stop_bid()

            self.assertTrue(fdm.bools)
            self.assertTrue(tdm.bools)
            self.assertTrue(len(Bid.query.filter_by(player_id=1).all()) == 1)
            self.assertTrue(len(Bid.query.filter_by(player_id=33).all()) == 1)
            self.assertTrue(carson.owner == carson_owner)
            self.assertTrue(ty.owner == ty_owner)
            self.assertTrue(bidState.number == 0)

            # rd 2
            bidding.start_bid()
            self.assertTrue(bidState.number == 1)
            self.assertTrue(bidState.bools)
            self.assertFalse(fdm.bools)
            self.assertFalse(tdm.bools)
            self.assertFalse(carson.upForBid)
            self.assertFalse(ty.upForBid)
            self.assertTrue(gordon.upForBid)
            self.assertTrue(mixon.upForBid)

            mixon_owner = mixon.owner
            gordon_owner = gordon.owner

            bidding.stop_bid()
            self.assertTrue(fdm.bools)
            self.assertTrue(tdm.bools)
            self.assertTrue(len(Bid.query.filter_by(player_id=25).all()) == 1)
            self.assertTrue(len(Bid.query.filter_by(player_id=77).all()) == 1)
            self.assertTrue(mixon.owner == mixon_owner)
            self.assertTrue(gordon.owner == gordon_owner)
            self.assertTrue(bidState.number == 1)

            # rd 3
            bidding.start_bid()
            self.assertTrue(bidState.number == 2)
            self.assertTrue(bidState.bools)
            self.assertFalse(fdm.bools)
            self.assertFalse(tdm.bools)
            self.assertFalse(carson.upForBid)
            self.assertFalse(ty.upForBid)
            self.assertFalse(gordon.upForBid)
            self.assertFalse(mixon.upForBid)

            # Dalvin Cook and Derrick Henry
            dalvin = Player.query.get(144)
            dalvin_owner = dalvin.owner
            derrick = Player.query.get(40)
            derrick_owner = derrick.owner

            # craig should win this with his second round pick
            bid1 = Bid(derrick.id, danny.id, 30, DraftPick.query.filter_by(
                owner_id=danny.id).filter_by(draftRound=2).first().pickInRound)
            bid2 = Bid(derrick.id, shaun.id, 40, "money")
            bid3 = Bid(derrick.id, craig.id, 40, DraftPick.query.filter_by(
                owner_id=craig.id).filter_by(draftRound=2).first().pickInRound)

            # craig will win with money
            bid4 = Bid(dalvin.id, shaun.id, 39, DraftPick.query.filter_by(
                owner_id=shaun.id).filter_by(draftRound=1).first().pickInRound)
            bid5 = Bid(dalvin.id, craig.id, 40, "money")
            bids = [bid1, bid2, bid3, bid4, bid5]
            db.session.add_all(bids)
            db.session.commit()

            bidding.stop_bid()
            self.assertFalse(fdm.bools)
            self.assertFalse(tdm.bools)
            self.assertTrue(len(Bid.query.filter_by(player_id=dalvin.id).all()) == 2)
            self.assertTrue(len(Bid.query.filter_by(player_id=derrick.id).all()) == 3)
            self.assertTrue(dalvin.owner == dalvin_owner)
            self.assertTrue(derrick.owner == derrick_owner)
            self.assertTrue(bidState.number == 2)
            winningTrans = Bid.query.filter_by(player_id=derrick.id).filter_by(winningBid=True).one()
            winningFran = Bid.query.filter_by(player_id=dalvin.id).filter_by(winningBid=True).one()
            self.assertEqual(winningTrans, bid3)
            self.assertEqual(winningFran, bid5)

            # one will make a decision, one will not
            bidding.process_match_release_player("TRANS", "match", 2)
            self.assertTrue(tdm.bools)
            self.assertFalse(fdm.bools)
            self.assertTrue(derrick.owner == derrick_owner)

            # now, time had run out.  Start bid again, which should run cleanup.  Dalvin should change hands
            # rd 4
            bidding.start_bid()

            self.assertFalse(dalvin.owner == dalvin_owner)
            self.assertTrue(dalvin.owner == craig)

            self.assertTrue(bidState.number == 3)
            self.assertTrue(bidState.bools)
            self.assertFalse(fdm.bools)
            self.assertFalse(tdm.bools)
            self.assertFalse(dalvin.upForBid)
            self.assertFalse(derrick.upForBid)

            calvin = Player.query.get(64)
            hopkins = Player.query.get(163)
            calvin_owner = calvin.owner
            hopkins_owner = hopkins.owner

            # danny should win this with his second round pick
            bid1 = Bid(calvin.id, danny.id, 40, DraftPick.query.filter_by(
                owner_id=danny.id).filter_by(draftRound=2).first().pickInRound)
            bid3 = Bid(calvin.id, craig.id, 40, DraftPick.query.filter_by(
                owner_id=craig.id).filter_by(draftRound=2).first().pickInRound)

            # danny will win with first round pick
            bid4 = Bid(hopkins.id, shaun.id, 39, DraftPick.query.filter_by(
                owner_id=shaun.id).filter_by(draftRound=1).first().pickInRound)
            bid5 = Bid(hopkins.id, danny.id, 40, DraftPick.query.filter_by(
                owner_id=danny.id).filter_by(draftRound=1).first().pickInRound)
            bids = [bid1, bid3, bid4, bid5]
            db.session.add_all(bids)
            db.session.commit()

            bidding.stop_bid()
            self.assertFalse(fdm.bools)
            self.assertFalse(tdm.bools)
            self.assertTrue(len(Bid.query.filter_by(player_id=hopkins.id).all()) == 2)
            self.assertTrue(len(Bid.query.filter_by(player_id=calvin.id).all()) == 2)
            self.assertTrue(calvin.owner == calvin_owner)
            self.assertTrue(hopkins.owner == hopkins_owner)
            self.assertTrue(bidState.number == 3)
            winningTrans = Bid.query.filter_by(player_id=calvin.id).filter_by(winningBid=True).one()
            winningFran = Bid.query.filter_by(player_id=hopkins.id).filter_by(winningBid=True).one()
            self.assertEqual(winningTrans, bid1)
            self.assertEqual(winningFran, bid5)

            # trans will release, fran will match
            bidding.process_match_release_player("TRANS", "release", 2)
            self.assertTrue(tdm.bools)
            self.assertFalse(fdm.bools)
            self.assertFalse(calvin.owner == calvin_owner)
            self.assertTrue(calvin.owner == danny)

            bidding.process_match_release_player("FRAN", "match", 1)
            self.assertTrue(tdm.bools)
            self.assertTrue(fdm.bools)
            self.assertTrue(hopkins.owner == hopkins_owner)
            self.assertFalse(hopkins.owner == danny)

            # start round 5 and skip ahead to round 6, where there are no franchise players left.
            bidding.start_bid()
            bidding.stop_bid()
            # rd 6
            bidding.start_bid()
            bidding.stop_bid()
            # rd 7
            bidding.start_bid()
            self.assertTrue(bidState.number == 6)
            bidding.stop_bid()
            # rd 8
            bidding.start_bid()
            bidding.stop_bid()
            # rd 9
            bidding.start_bid()
            bidding.stop_bid()
            # this should be the end
            bidding.start_bid()


if __name__ == '__main__':
    unittest.main()
