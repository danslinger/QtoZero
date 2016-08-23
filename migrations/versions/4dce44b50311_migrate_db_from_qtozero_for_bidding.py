"""Migrate db from qtozero for bidding

Revision ID: 4dce44b50311
Revises: 4ea4dde67d60
Create Date: 2016-08-02 22:06:12.992615

"""

# revision identifiers, used by Alembic.
revision = '4dce44b50311'
down_revision = '4ea4dde67d60'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('states',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=16), nullable=True),
    sa.Column('number', sa.Integer(), nullable=True),
    sa.Column('bools', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column(u'bids', sa.Column('winningAmount', sa.Integer(), nullable=True))
    op.add_column(u'bids', sa.Column('winningBid', sa.Boolean(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column(u'bids', 'winningBid')
    op.drop_column(u'bids', 'winningAmount')
    op.drop_table('states')
    ### end Alembic commands ###