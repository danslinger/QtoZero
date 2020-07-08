from flask import render_template
from flask_login import login_required
from app.models.owner import Owner
from . import main


@main.route('/contacts')
@login_required
def contacts():
    owners = Owner.query.all()
    return render_template('contacts.html',
                           owners=owners)
