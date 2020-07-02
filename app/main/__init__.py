''' main blueprint '''
from flask import Blueprint

main = Blueprint('main', __name__)

from . import errors
from . import routes_bidding
from . import routes_contacts
from . import routes_draft_order
from . import routes_keepers
from . import routes_login
from . import routes_probowl
from . import routes_tags
