"""Prep for bidding, add draft pick and bidding tables

Revision ID: 4ea4dde67d60
Revises: 3d7b7f0945b
Create Date: 2016-07-20 02:28:32.649267

"""

# revision identifiers, used by Alembic.
revision = '4ea4dde67d60'
down_revision = '3d7b7f0945b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('draftpicks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('draftRound', sa.Integer(), nullable=True),
    sa.Column('pickInRound', sa.Integer(), nullable=True),
    sa.Column('owner_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['owner_id'], ['owners.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('bids',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('player_id', sa.Integer(), nullable=True),
    sa.Column('owner_bidding_id', sa.Integer(), nullable=True),
    sa.Column('amount', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['owner_bidding_id'], ['owners.id'], ),
    sa.ForeignKeyConstraint(['player_id'], ['players.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column(u'owners', sa.Column('madeBid', sa.Boolean(), nullable=True))
    op.add_column(u'players', sa.Column('finishedBidding', sa.Boolean(), nullable=True))
    op.add_column(u'players', sa.Column('upForBid', sa.Boolean(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column(u'players', 'upForBid')
    op.drop_column(u'players', 'finishedBidding')
    op.drop_column(u'owners', 'madeBid')
    op.drop_table('bids')
    op.drop_table('draftpicks')
    ### end Alembic commands ###
