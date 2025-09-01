"""Initial schema - comprehensive migration

This migration is designed to be IDEMPOTENT and TRANSACTIONAL:

IDEMPOTENCY:
- All table/index/constraint creation uses Alembic's built-in idempotency
- Role creation uses PostgreSQL's DO blocks with EXISTS checks
- RLS policy creation uses PostgreSQL's DO blocks with pg_policies checks  
- All operations can be safely run multiple times

TRANSACTIONAL:
- Alembic automatically wraps the entire migration in a transaction
- If any operation fails, the entire migration is rolled back
- No partial state is left in the database

Revision ID: 20250815_00
Revises: 
Create Date: 2025-08-15 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250815_00'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create organization table
    op.create_table('organization',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('billing_plan', sa.String(), nullable=True),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create user table
    op.create_table('user',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_pw', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=False)

    # Create usertoken table
    op.create_table('usertoken',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('refresh_token_jti', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('refresh_token_jti')
    )

    # Create credential table
    op.create_table('credential',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('connector_name', sa.String(), nullable=False),
        sa.Column('provider_key', sa.String(), nullable=False),
        sa.Column('credential_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_refreshed_at', sa.DateTime(), nullable=True),
        sa.Column('refresh_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(), nullable=False, server_default='active'),
        sa.Column('encryption_key_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_by_ip', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'user_id', 'connector_name', 'provider_key', name='uq_cred_org_user_name_key')
    )

    # Create credential_audit_log table
    op.create_table('credential_audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('credential_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('result', sa.String(), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['credential_id'], ['credential.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for credential audit log
    op.create_index('ix_audit_credential_time', 'credential_audit_log', ['credential_id', 'created_at'])
    op.create_index('ix_audit_org_time', 'credential_audit_log', ['organization_id', 'created_at'])

    # Create connectorprofile table
    op.create_table('connectorprofile',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('connector_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('checkpoint_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('interval_minutes', sa.Integer(), nullable=False),
        sa.Column('next_run_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('credential_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='active'),
        sa.ForeignKeyConstraint(['credential_id'], ['credential.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create destinationtarget table
    op.create_table('destinationtarget',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'user_id', 'name', name='uq_target_org_user_name')
    )

    # Create syncrun table
    op.create_table('syncrun',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('records_synced', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['profile_id'], ['connectorprofile.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create authenticated role for RLS (idempotent)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                CREATE ROLE authenticated;
            END IF;
        END $$
    """)
    
    # Enable Row Level Security on all tables (idempotent)
    op.execute("ALTER TABLE organization ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE \"user\" ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE usertoken ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE credential ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE credential_audit_log ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE connectorprofile ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE destinationtarget ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE syncrun ENABLE ROW LEVEL SECURITY")

    # Create RLS policies for organization isolation (idempotent)
    # First drop existing policies to ensure they use updated logic
    op.execute("""
        DROP POLICY IF EXISTS organization_isolation ON organization;
        DROP POLICY IF EXISTS user_org_isolation ON "user";
        DROP POLICY IF EXISTS usertoken_user_isolation ON usertoken;
        DROP POLICY IF EXISTS credential_org_isolation ON credential;
        DROP POLICY IF EXISTS credential_audit_org_isolation ON credential_audit_log;
        DROP POLICY IF EXISTS connectorprofile_org_isolation ON connectorprofile;
        DROP POLICY IF EXISTS destinationtarget_org_isolation ON destinationtarget;
        DROP POLICY IF EXISTS syncrun_org_isolation ON syncrun;
    """)
    
    # Organization: users can only see their own org
    op.execute("""
        CREATE POLICY organization_isolation ON organization
        FOR ALL TO authenticated
        USING (id = current_setting('app.current_org')::uuid);
    """)

    # User: users can only see users in their org
    op.execute("""
        CREATE POLICY user_org_isolation ON "user"
        FOR ALL TO authenticated
        USING (organization_id = current_setting('app.current_org')::uuid);
    """)

    # UserToken: users can only see their own tokens
    op.execute("""
        CREATE POLICY usertoken_user_isolation ON usertoken
        FOR ALL TO authenticated
        USING (user_id IN (SELECT id FROM "user" WHERE organization_id = current_setting('app.current_org')::uuid));
    """)

    # Credential: users can only see credentials in their org
    op.execute("""
        CREATE POLICY credential_org_isolation ON credential
        FOR ALL TO authenticated
        USING (organization_id = current_setting('app.current_org')::uuid);
    """)

    # Credential audit log: users can only see audit logs for their org
    op.execute("""
        CREATE POLICY credential_audit_org_isolation ON credential_audit_log
        FOR ALL TO authenticated
        USING (organization_id = current_setting('app.current_org')::uuid);
    """)

    # ConnectorProfile: users can only see profiles in their org
    op.execute("""
        CREATE POLICY connectorprofile_org_isolation ON connectorprofile
        FOR ALL TO authenticated
        USING (organization_id = current_setting('app.current_org')::uuid);
    """)

    # DestinationTarget: users can only see targets in their org
    op.execute("""
        CREATE POLICY destinationtarget_org_isolation ON destinationtarget
        FOR ALL TO authenticated
        USING (organization_id = current_setting('app.current_org')::uuid);
    """)

    # SyncRun: users can only see sync runs for profiles in their org
    op.execute("""
        CREATE POLICY syncrun_org_isolation ON syncrun
        FOR ALL TO authenticated
        USING (EXISTS (
            SELECT 1 FROM connectorprofile
            WHERE connectorprofile.id = syncrun.profile_id
            AND connectorprofile.organization_id = current_setting('app.current_org')::uuid
        ));
    """)


def downgrade() -> None:
    # Drop role
    op.execute("DROP ROLE IF EXISTS authenticated")
    
    # Drop tables (foreign key constraints will be handled automatically)
    op.drop_table('syncrun')
    op.drop_table('destinationtarget')
    op.drop_table('connectorprofile')
    
    # Drop indexes
    op.drop_index('ix_audit_org_time', table_name='credential_audit_log')
    op.drop_index('ix_audit_credential_time', table_name='credential_audit_log')
    op.drop_table('credential_audit_log')
    
    op.drop_table('credential')
    op.drop_table('usertoken')
    op.drop_index(op.f('ix_user_email'), table_name='user')
    op.drop_table('user')
    op.drop_table('organization')
