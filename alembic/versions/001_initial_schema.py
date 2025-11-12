"""Initial schema with managers, issuers, filings, and holdings

Revision ID: 001
Revises:
Create Date: 2025-01-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create managers table
    op.create_table(
        'managers',
        sa.Column('cik', sa.String(length=10), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.PrimaryKeyConstraint('cik'),
    )
    op.create_index(op.f('ix_managers_cik'), 'managers', ['cik'], unique=False)

    # Create issuers table
    op.create_table(
        'issuers',
        sa.Column('cusip', sa.String(length=9), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('figi', sa.String(length=12), nullable=True),
        sa.PrimaryKeyConstraint('cusip'),
    )
    op.create_index(op.f('ix_issuers_cusip'), 'issuers', ['cusip'], unique=False)
    op.create_index(op.f('ix_issuers_figi'), 'issuers', ['figi'], unique=False)

    # Create filings table
    op.create_table(
        'filings',
        sa.Column('accession_number', sa.String(length=25), nullable=False),
        sa.Column('cik', sa.String(length=10), nullable=False),
        sa.Column('filing_date', sa.Date(), nullable=False),
        sa.Column('period_of_report', sa.Date(), nullable=False),
        sa.Column('submission_type', sa.String(length=10), nullable=False),
        sa.Column('report_type', sa.String(length=30), nullable=False),
        sa.Column('total_value', sa.BigInteger(), nullable=False),
        sa.Column('number_of_holdings', sa.Integer(), nullable=False),
        sa.CheckConstraint('total_value >= 0', name='check_total_value_positive'),
        sa.CheckConstraint('number_of_holdings >= 0', name='check_holdings_count_positive'),
        sa.ForeignKeyConstraint(['cik'], ['managers.cik'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('accession_number'),
    )
    op.create_index(op.f('ix_filings_accession_number'), 'filings', ['accession_number'], unique=False)
    op.create_index(op.f('ix_filings_cik'), 'filings', ['cik'], unique=False)
    op.create_index(op.f('ix_filings_filing_date'), 'filings', ['filing_date'], unique=False)
    op.create_index(op.f('ix_filings_period_of_report'), 'filings', ['period_of_report'], unique=False)
    op.create_index(op.f('ix_filings_total_value'), 'filings', ['total_value'], unique=False)
    op.create_index('ix_filings_cik_period', 'filings', ['cik', 'period_of_report'], unique=False)
    op.create_index('ix_filings_period_value', 'filings', ['period_of_report', 'total_value'], unique=False)

    # Create holdings table
    op.create_table(
        'holdings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('accession_number', sa.String(length=25), nullable=False),
        sa.Column('cusip', sa.String(length=9), nullable=False),
        sa.Column('title_of_class', sa.String(length=150), nullable=False),
        sa.Column('value', sa.BigInteger(), nullable=False),
        sa.Column('shares_or_principal', sa.BigInteger(), nullable=False),
        sa.Column('sh_or_prn', sa.String(length=10), nullable=False),
        sa.Column('investment_discretion', sa.String(length=10), nullable=False),
        sa.Column('put_call', sa.String(length=10), nullable=True),
        sa.Column('voting_authority_sole', sa.BigInteger(), nullable=False),
        sa.Column('voting_authority_shared', sa.BigInteger(), nullable=False),
        sa.Column('voting_authority_none', sa.BigInteger(), nullable=False),
        sa.CheckConstraint('value >= 0', name='check_value_positive'),
        sa.CheckConstraint('shares_or_principal >= 0', name='check_shares_positive'),
        sa.CheckConstraint('voting_authority_sole >= 0', name='check_voting_sole_positive'),
        sa.CheckConstraint('voting_authority_shared >= 0', name='check_voting_shared_positive'),
        sa.CheckConstraint('voting_authority_none >= 0', name='check_voting_none_positive'),
        sa.ForeignKeyConstraint(['accession_number'], ['filings.accession_number'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cusip'], ['issuers.cusip'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_holdings_accession_number'), 'holdings', ['accession_number'], unique=False)
    op.create_index(op.f('ix_holdings_cusip'), 'holdings', ['cusip'], unique=False)
    op.create_index(op.f('ix_holdings_value'), 'holdings', ['value'], unique=False)
    op.create_index('ix_holdings_accession_cusip', 'holdings', ['accession_number', 'cusip'], unique=False)
    op.create_index('ix_holdings_cusip_value', 'holdings', ['cusip', 'value'], unique=False)
    op.create_index(
        'ix_holdings_value_desc',
        'holdings',
        [sa.text('value DESC')],
        unique=False,
        postgresql_ops={'value': 'DESC'}
    )


def downgrade() -> None:
    op.drop_index('ix_holdings_value_desc', table_name='holdings')
    op.drop_index('ix_holdings_cusip_value', table_name='holdings')
    op.drop_index('ix_holdings_accession_cusip', table_name='holdings')
    op.drop_index(op.f('ix_holdings_value'), table_name='holdings')
    op.drop_index(op.f('ix_holdings_cusip'), table_name='holdings')
    op.drop_index(op.f('ix_holdings_accession_number'), table_name='holdings')
    op.drop_table('holdings')

    op.drop_index('ix_filings_period_value', table_name='filings')
    op.drop_index('ix_filings_cik_period', table_name='filings')
    op.drop_index(op.f('ix_filings_total_value'), table_name='filings')
    op.drop_index(op.f('ix_filings_period_of_report'), table_name='filings')
    op.drop_index(op.f('ix_filings_filing_date'), table_name='filings')
    op.drop_index(op.f('ix_filings_cik'), table_name='filings')
    op.drop_index(op.f('ix_filings_accession_number'), table_name='filings')
    op.drop_table('filings')

    op.drop_index(op.f('ix_issuers_figi'), table_name='issuers')
    op.drop_index(op.f('ix_issuers_cusip'), table_name='issuers')
    op.drop_table('issuers')

    op.drop_index(op.f('ix_managers_cik'), table_name='managers')
    op.drop_table('managers')
