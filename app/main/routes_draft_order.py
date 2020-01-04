from flask import render_template
from flask_login import login_required
from app.models.draft_pick import DraftPick
from . import main


@main.route('/draft_order', methods=['GET'])
@login_required
def draft_order():
    draft_picks = DraftPick.query.all()
    return render_template('draftOrder.html', draftPicks=draft_picks)
