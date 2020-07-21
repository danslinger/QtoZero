import os
from app.models.states import States
from app import db, create_app


def main():
    # noinspection PyUnusedLocal
    create_app(os.getenv('FLASK_CONFIG')
               or 'default').app_context().push()
    states = [States(name="biddingOn"), States(name="franchiseDecisionMade"), States(name="transitionDecisionMade")]
    States.query.delete()
    db.session.add_all(states)
    db.session.commit()


if __name__ == '__main__':
    main()
