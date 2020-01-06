import os
import json
import requests
import player_setup
from app.models.owner import Owner
from app import create_app
from tokens import tokens
from SlackBot import SlackBot
from constants import LEAGUE_ID, MFL_URL
from local_settings import let_bot_post

api_token = tokens['mfl_token']
channel = "general"
bot = SlackBot()


def calculate_salary(owner):
    total = sum(p.salary for p in owner.players if p.status == "ROSTER")
    total += sum(p.salary * .30 for p in owner.players if p.status ==
                 "INJURED RESERVE")
    return total


def get_salary_cap(_league_data):
    base_cap = _league_data['salaryCapAmount']
    caps = dict()
    for franchise in league_data['franchises']['franchise']:
        if franchise['salaryCapAmount'] != '':
            caps[franchise['id']] = franchise['salaryCapAmount']
        else:
            caps[franchise['id']] = base_cap
    return caps


def get_league_info():
    payload = {'TYPE': 'league',
               'JSON': 1,
               'L': LEAGUE_ID,
               }
    r = requests.get(MFL_URL, params=payload)
    return json.loads(r.content)['league']


def identify_owners_over_cap(salary_cap_limits):
    over_the_cap = dict()
    for owner_id, cap_limit in salary_cap_limits.items():
        total_salary = calculate_salary(
            Owner.query.filter_by(mfl_team_id=owner_id).first())
        if total_salary > int(cap_limit):
            over_the_cap[owner_id] = {'cap_limit': cap_limit,
                                      'total_salary': total_salary,
                                      'amount_over': int(cap_limit) - total_salary}
        else:
            print(total_salary, cap_limit, owner_id)
    return over_the_cap


def create_over_cap_message(over_the_cap_owners):
    message = "The following owner(s) currently have rosters that are over their salary cap:\n\n "
    for owner_id, cap_info in over_the_cap_owners.items():
        owner = Owner.query.filter_by(mfl_team_id=owner_id).first()
        message += f'{owner.team_name} is over the cap by ${cap_info["amount_over"]}. ' \
                   f'Total roster salary is ${cap_info["total_salary"]} and their salary '\
                   f'cap is ${cap_info["cap_limit"]}\n\n'
    return message


def check_salary_cap(_league_data):

    salary_cap_limits = get_salary_cap(_league_data)
    owners_over_the_cap = identify_owners_over_cap(salary_cap_limits)
    if owners_over_the_cap:
        message = create_over_cap_message(owners_over_the_cap)
        if let_bot_post:
            bot.post_message(channel, message)
        else:
            print(message)


def create_player_count_message(owner_count):
    message = ''
    for owner, count in owner_count.items():
        message += f"{owner.team_name} currently has {count} players.  Fix it!\n\n"
    return message


def check_player_count():
    owners = Owner.query.all()
    owner_count = dict()
    for owner in owners:
        total_players = sum(1 for p in owner.players if p.status == "ROSTER")
        if total_players > 16:
            owner_count[owner] = total_players
    if owner_count:
        message = create_player_count_message(owner_count)
        if let_bot_post:
            bot.post_message(channel, message)
        else:
            print(message)


if __name__ == '__main__':
    player_setup.main()
    create_app(os.getenv('FLASK_CONFIG') or 'default').app_context().push()
    league_data = get_league_info()
    check_salary_cap(league_data)
    check_player_count()
