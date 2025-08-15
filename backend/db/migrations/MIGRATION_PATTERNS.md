# Database Migration Patterns

This document outlines the required patterns for all database migrations in this project.

## Core Principles

### 1. IDEMPOTENCY
All migrations must be **idempotent** - they can be run multiple times safely without causing errors or unwanted side effects.

### 2. TRANSACTIONAL
All migrations are **transactional** - Alembic automatically wraps each migration in a database transaction. If any operation fails, the entire migration is rolled back.

## Implementation Patterns

### Table Creation
✅ **GOOD** - Alembic handles idempotency automatically:
```python
op.create_table('mytable',
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('name', sa.String(50), nullable=False)
)
```

### Role Creation
✅ **GOOD** - Use DO blocks with EXISTS checks:
```python
op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'my_role') THEN
            CREATE ROLE my_role;
        END IF;
    END $$
""")
```

❌ **BAD** - Will fail on second run:
```python
op.execute("CREATE ROLE my_role")
```

### Policy Creation
✅ **GOOD** - Use DO blocks with pg_policies checks:
```python
op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'mytable' AND policyname = 'my_policy') THEN
            CREATE POLICY my_policy ON mytable FOR ALL TO my_role USING (true);
        END IF;
    END $$
""")
```

❌ **BAD** - Will fail on second run:
```python
op.execute("CREATE POLICY my_policy ON mytable FOR ALL TO my_role USING (true)")
```

### Function Creation
✅ **GOOD** - Use CREATE OR REPLACE:
```python
op.execute("""
    CREATE OR REPLACE FUNCTION my_function()
    RETURNS trigger AS $$
    BEGIN
        -- function body
    END;
    $$ LANGUAGE plpgsql;
""")
```

### Trigger Creation
✅ **GOOD** - Drop if exists, then create:
```python
op.execute("DROP TRIGGER IF EXISTS my_trigger ON mytable")
op.execute("""
    CREATE TRIGGER my_trigger
    AFTER INSERT ON mytable
    FOR EACH ROW EXECUTE FUNCTION my_function()
""")
```

### Data Operations
⚠️ **CAREFUL** - Data operations need special consideration:
```python
# Check if data already exists before inserting
op.execute("""
    INSERT INTO mytable (name) 
    SELECT 'default_value'
    WHERE NOT EXISTS (SELECT 1 FROM mytable WHERE name = 'default_value')
""")
```

## Testing Idempotency

Always test your migrations by running them twice:

```bash
# Run migration
alembic upgrade head

# Run again - should not fail
alembic upgrade head
```

## Downgrade Patterns

Downgrade functions should also be idempotent:

```python
def downgrade() -> None:
    # Use IF EXISTS for drops
    op.execute("DROP ROLE IF EXISTS my_role")
    op.drop_table('mytable')  # Alembic handles this
```

## Why This Matters

1. **Development**: Developers often need to reset and rerun migrations
2. **CI/CD**: Automated deployments may retry failed migrations
3. **Disaster Recovery**: Ability to safely re-apply migrations during recovery
4. **Container Environments**: Migrations may run multiple times during scaling events

## Migration Checklist

Before committing any migration, ensure:

- [ ] Can be run multiple times without error
- [ ] Uses appropriate idempotency patterns
- [ ] Has been tested by running twice locally
- [ ] Includes proper documentation/comments
- [ ] Downgrade function is also idempotent
