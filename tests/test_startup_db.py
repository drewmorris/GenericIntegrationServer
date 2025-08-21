"""
Tests for database startup and initialization utilities
"""
import pytest
import os
import logging
from unittest.mock import patch, MagicMock, call
from sqlalchemy.exc import OperationalError

from backend.db.startup import (
    initialize_database,
    _database_available,
    _get_database_url,
    _run_migrations
)


class TestInitializeDatabase:
    """Test initialize_database function"""
    
    @patch('backend.db.startup._run_migrations')
    @patch('backend.db.startup._database_available')
    def test_initialize_database_success(self, mock_db_available, mock_run_migrations):
        """Test successful database initialization"""
        mock_db_available.return_value = True
        
        # Should not raise any exception
        initialize_database()
        
        mock_db_available.assert_called_once()
        mock_run_migrations.assert_called_once()
    
    @patch('backend.db.startup._run_migrations')
    @patch('backend.db.startup._database_available')
    def test_initialize_database_not_available(self, mock_db_available, mock_run_migrations):
        """Test database initialization when database is not available"""
        mock_db_available.return_value = False
        
        # Should not raise any exception
        initialize_database()
        
        mock_db_available.assert_called_once()
        mock_run_migrations.assert_not_called()
    
    @patch('backend.db.startup._run_migrations')
    @patch('backend.db.startup._database_available')
    def test_initialize_database_migration_failure(self, mock_db_available, mock_run_migrations):
        """Test database initialization when migrations fail"""
        mock_db_available.return_value = True
        mock_run_migrations.side_effect = Exception("Migration failed")
        
        # Should not raise exception, but log error and continue
        initialize_database()
        
        mock_db_available.assert_called_once()
        mock_run_migrations.assert_called_once()
    
    @patch('backend.db.startup._database_available')
    def test_initialize_database_availability_check_failure(self, mock_db_available):
        """Test database initialization when availability check fails"""
        mock_db_available.side_effect = Exception("Connection error")
        
        # Should not raise exception, but log error and continue
        initialize_database()
        
        mock_db_available.assert_called_once()


class TestDatabaseAvailable:
    """Test _database_available function"""
    
    @patch('backend.db.startup.create_engine')
    @patch('backend.db.startup._get_database_url')
    def test_database_available_success(self, mock_get_url, mock_create_engine):
        """Test successful database availability check"""
        mock_get_url.return_value = "postgresql://user:pass@host:5432/db"
        
        # Mock engine and connection
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_create_engine.return_value = mock_engine
        
        result = _database_available()
        
        assert result is True
        mock_create_engine.assert_called_once_with("postgresql://user:pass@host:5432/db")
        mock_engine.connect.assert_called_once()
        mock_conn.execute.assert_called_once()
        mock_engine.dispose.assert_called_once()
    
    @patch('backend.db.startup.create_engine')
    @patch('backend.db.startup._get_database_url')
    def test_database_available_connection_failure(self, mock_get_url, mock_create_engine):
        """Test database availability check with connection failure"""
        mock_get_url.return_value = "postgresql://user:pass@host:5432/db"
        mock_create_engine.side_effect = OperationalError("Connection failed", None, None)
        
        result = _database_available()
        
        assert result is False
        mock_create_engine.assert_called_once()
    
    @patch('backend.db.startup.create_engine')
    @patch('backend.db.startup._get_database_url')
    def test_database_available_query_failure(self, mock_get_url, mock_create_engine):
        """Test database availability check with query failure"""
        mock_get_url.return_value = "postgresql://user:pass@host:5432/db"
        
        # Mock engine that connects but query fails
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("Query failed")
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_create_engine.return_value = mock_engine
        
        result = _database_available()
        
        assert result is False
        mock_create_engine.assert_called_once()
        mock_engine.connect.assert_called_once()
        mock_conn.execute.assert_called_once()


class TestGetDatabaseUrl:
    """Test _get_database_url function"""
    
    def test_get_database_url_defaults(self):
        """Test database URL generation with default values"""
        with patch.dict(os.environ, {}, clear=True):
            url = _get_database_url()
            expected = "postgresql://postgres:postgres@localhost:5432/integration_server"
            assert url == expected
    
    def test_get_database_url_custom_values(self):
        """Test database URL generation with custom environment variables"""
        env_vars = {
            "POSTGRES_HOST": "custom-host",
            "POSTGRES_PORT": "5433",
            "POSTGRES_USER": "custom-user",
            "POSTGRES_PASSWORD": "custom-pass",
            "POSTGRES_DB": "custom-db"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            url = _get_database_url()
            expected = "postgresql://custom-user:custom-pass@custom-host:5433/custom-db"
            assert url == expected
    
    def test_get_database_url_partial_custom(self):
        """Test database URL generation with some custom environment variables"""
        env_vars = {
            "POSTGRES_HOST": "prod-db",
            "POSTGRES_USER": "app-user"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            url = _get_database_url()
            expected = "postgresql://app-user:postgres@prod-db:5432/integration_server"
            assert url == expected
    
    def test_get_database_url_empty_values(self):
        """Test database URL generation with empty environment variables"""
        env_vars = {
            "POSTGRES_HOST": "",
            "POSTGRES_PORT": "",
            "POSTGRES_USER": "",
            "POSTGRES_PASSWORD": "",
            "POSTGRES_DB": ""
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            url = _get_database_url()
            # Empty values are used as-is (not falling back to defaults)
            expected = "postgresql://:@:/"
            assert url == expected


class TestRunMigrations:
    """Test _run_migrations function"""
    
    @patch('backend.db.startup.command')
    @patch('backend.db.startup.Config')
    @patch('backend.db.startup._get_database_url')
    def test_run_migrations_success(self, mock_get_url, mock_config_class, mock_command):
        """Test successful migration run"""
        mock_get_url.return_value = "postgresql://user:pass@host:5432/db"
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config
        
        _run_migrations()
        
        mock_config_class.assert_called_once_with("backend/alembic.ini")
        mock_config.set_main_option.assert_called_once_with(
            "sqlalchemy.url", "postgresql://user:pass@host:5432/db"
        )
        mock_command.upgrade.assert_called_once_with(mock_config, "head")
    
    @patch('backend.db.startup.command')
    @patch('backend.db.startup.Config')
    @patch('backend.db.startup._get_database_url')
    def test_run_migrations_failure(self, mock_get_url, mock_config_class, mock_command):
        """Test migration run failure"""
        mock_get_url.return_value = "postgresql://user:pass@host:5432/db"
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config
        mock_command.upgrade.side_effect = Exception("Migration failed")
        
        with pytest.raises(Exception, match="Migration failed"):
            _run_migrations()
        
        mock_config_class.assert_called_once_with("backend/alembic.ini")
        mock_config.set_main_option.assert_called_once()
        mock_command.upgrade.assert_called_once_with(mock_config, "head")
    
    @patch('backend.db.startup.command')
    @patch('backend.db.startup.Config')
    @patch('backend.db.startup._get_database_url')
    def test_run_migrations_config_failure(self, mock_get_url, mock_config_class, mock_command):
        """Test migration run with config creation failure"""
        mock_get_url.return_value = "postgresql://user:pass@host:5432/db"
        mock_config_class.side_effect = Exception("Config failed")
        
        with pytest.raises(Exception, match="Config failed"):
            _run_migrations()
        
        mock_config_class.assert_called_once_with("backend/alembic.ini")
        mock_command.upgrade.assert_not_called()


class TestLoggingBehavior:
    """Test logging behavior during startup"""
    
    @patch('backend.db.startup.logging.getLogger')
    @patch('backend.db.startup.command')
    @patch('backend.db.startup.Config')
    @patch('backend.db.startup._get_database_url')
    def test_run_migrations_logging_levels(self, mock_get_url, mock_config_class, mock_command, mock_get_logger):
        """Test that Alembic logging is properly managed during migrations"""
        mock_get_url.return_value = "postgresql://user:pass@host:5432/db"
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config
        
        # Mock the alembic logger
        mock_alembic_logger = MagicMock()
        mock_get_logger.return_value = mock_alembic_logger
        
        _run_migrations()
        
        # Verify getLogger was called for alembic (at least once)
        assert mock_get_logger.call_count >= 2
        # Verify that "alembic" was passed to getLogger calls
        alembic_calls = [call for call in mock_get_logger.call_args_list if call[0][0] == "alembic"]
        assert len(alembic_calls) == 2
        
        # Verify setLevel was called to suppress then restore
        assert mock_alembic_logger.setLevel.call_count == 2
        calls = mock_alembic_logger.setLevel.call_args_list
        assert calls[0][0][0] == logging.WARNING  # Suppress logs
        assert calls[1][0][0] == logging.INFO     # Restore logs
    
    @patch('backend.db.startup.logging.getLogger')
    @patch('backend.db.startup.command')
    @patch('backend.db.startup.Config')
    @patch('backend.db.startup._get_database_url')
    def test_run_migrations_logging_restored_on_failure(self, mock_get_url, mock_config_class, mock_command, mock_get_logger):
        """Test that Alembic logging is restored even when migration fails"""
        mock_get_url.return_value = "postgresql://user:pass@host:5432/db"
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config
        mock_command.upgrade.side_effect = Exception("Migration failed")
        
        # Mock the alembic logger
        mock_alembic_logger = MagicMock()
        mock_get_logger.return_value = mock_alembic_logger
        
        with pytest.raises(Exception, match="Migration failed"):
            _run_migrations()
        
        # Verify logging was still restored in finally block
        assert mock_alembic_logger.setLevel.call_count == 2
        calls = mock_alembic_logger.setLevel.call_args_list
        assert calls[0][0][0] == logging.WARNING  # Suppress logs
        assert calls[1][0][0] == logging.INFO     # Restore logs (in finally)


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases"""
    
    @patch('backend.db.startup._run_migrations')
    @patch('backend.db.startup._database_available')
    def test_full_startup_flow_success(self, mock_db_available, mock_run_migrations):
        """Test complete successful startup flow"""
        mock_db_available.return_value = True
        
        initialize_database()
        
        # Verify the complete flow
        mock_db_available.assert_called_once()
        mock_run_migrations.assert_called_once()
    
    @patch('backend.db.startup.create_engine')
    @patch('backend.db.startup._get_database_url')
    def test_database_connection_cleanup(self, mock_get_url, mock_create_engine):
        """Test that database connections are properly cleaned up"""
        mock_get_url.return_value = "postgresql://user:pass@host:5432/db"
        
        # Mock engine that raises exception during connection
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("Connection failed")
        mock_create_engine.return_value = mock_engine
        
        result = _database_available()
        
        assert result is False
        # Engine should still be created even if connection fails
        mock_create_engine.assert_called_once()
        # dispose should not be called if connection fails before context manager
        mock_engine.dispose.assert_not_called()
    
    def test_environment_variable_precedence(self):
        """Test that environment variables take precedence over defaults"""
        # Test with mixed environment variables
        env_vars = {
            "POSTGRES_HOST": "env-host",
            "POSTGRES_PORT": "9999"
            # Other vars should use defaults
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            url = _get_database_url()
            
            assert "env-host" in url
            assert "9999" in url
            assert "postgres:postgres" in url  # Default user:password
            assert "integration_server" in url  # Default database
