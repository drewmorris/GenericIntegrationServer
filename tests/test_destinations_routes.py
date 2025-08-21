"""
Tests for destinations routes
"""
import pytest
from unittest.mock import patch, MagicMock

from backend.routes.destinations import list_destination_definitions


class TestDestinationsRoutes:
    """Test destinations route functions"""
    
    @pytest.mark.asyncio
    async def test_list_destination_definitions_success(self):
        """Test successful destination definitions listing"""
        # Mock destination classes
        mock_dest1 = MagicMock()
        mock_dest1_instance = MagicMock()
        mock_dest1_instance.config_schema.return_value = {
            "type": "object",
            "properties": {
                "api_key": {"type": "string", "description": "API key"}
            },
            "required": ["api_key"]
        }
        mock_dest1.return_value = mock_dest1_instance
        
        mock_dest2 = MagicMock()
        mock_dest2_instance = MagicMock()
        mock_dest2_instance.config_schema.return_value = {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Endpoint URL"},
                "timeout": {"type": "integer", "description": "Timeout in seconds"}
            },
            "required": ["url"]
        }
        mock_dest2.return_value = mock_dest2_instance
        
        # Mock registry
        mock_registry = {
            "cleverbrag": mock_dest1,
            "webhook": mock_dest2
        }
        
        with patch('backend.routes.destinations.registry', mock_registry):
            result = await list_destination_definitions()
        
        assert len(result) == 2
        
        # Check first destination
        cleverbrag_def = next(d for d in result if d["name"] == "cleverbrag")
        assert cleverbrag_def["schema"]["properties"]["api_key"]["type"] == "string"
        assert "api_key" in cleverbrag_def["schema"]["required"]
        
        # Check second destination
        webhook_def = next(d for d in result if d["name"] == "webhook")
        assert webhook_def["schema"]["properties"]["url"]["type"] == "string"
        assert webhook_def["schema"]["properties"]["timeout"]["type"] == "integer"
        assert "url" in webhook_def["schema"]["required"]
        
        # Verify instances were created and config_schema was called
        mock_dest1.assert_called_once()
        mock_dest1_instance.config_schema.assert_called_once()
        mock_dest2.assert_called_once()
        mock_dest2_instance.config_schema.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_destination_definitions_empty_registry(self):
        """Test destination definitions listing with empty registry"""
        mock_registry = {}
        
        with patch('backend.routes.destinations.registry', mock_registry):
            result = await list_destination_definitions()
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_list_destination_definitions_single_destination(self):
        """Test destination definitions listing with single destination"""
        mock_dest = MagicMock()
        mock_dest_instance = MagicMock()
        mock_dest_instance.config_schema.return_value = {
            "type": "object",
            "properties": {
                "host": {"type": "string"},
                "port": {"type": "integer", "default": 443}
            }
        }
        mock_dest.return_value = mock_dest_instance
        
        mock_registry = {"single_dest": mock_dest}
        
        with patch('backend.routes.destinations.registry', mock_registry):
            result = await list_destination_definitions()
        
        assert len(result) == 1
        assert result[0]["name"] == "single_dest"
        assert result[0]["schema"]["properties"]["host"]["type"] == "string"
        assert result[0]["schema"]["properties"]["port"]["default"] == 443
    
    @pytest.mark.asyncio
    async def test_list_destination_definitions_with_complex_schema(self):
        """Test destination definitions with complex schema"""
        mock_dest = MagicMock()
        mock_dest_instance = MagicMock()
        mock_dest_instance.config_schema.return_value = {
            "type": "object",
            "properties": {
                "connection": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string"},
                        "port": {"type": "integer"},
                        "ssl": {"type": "boolean", "default": True}
                    },
                    "required": ["host", "port"]
                },
                "auth": {
                    "type": "object",
                    "properties": {
                        "username": {"type": "string"},
                        "password": {"type": "string"}
                    },
                    "required": ["username", "password"]
                },
                "options": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["connection", "auth"]
        }
        mock_dest.return_value = mock_dest_instance
        
        mock_registry = {"complex_dest": mock_dest}
        
        with patch('backend.routes.destinations.registry', mock_registry):
            result = await list_destination_definitions()
        
        assert len(result) == 1
        dest_def = result[0]
        assert dest_def["name"] == "complex_dest"
        
        schema = dest_def["schema"]
        assert "connection" in schema["properties"]
        assert "auth" in schema["properties"]
        assert "options" in schema["properties"]
        assert schema["properties"]["connection"]["type"] == "object"
        assert schema["properties"]["auth"]["type"] == "object"
        assert schema["properties"]["options"]["type"] == "array"
        assert set(schema["required"]) == {"connection", "auth"}
    
    @pytest.mark.asyncio
    async def test_list_destination_definitions_destination_instantiation_error(self):
        """Test when destination class instantiation fails"""
        mock_dest = MagicMock()
        mock_dest.side_effect = Exception("Instantiation failed")
        
        mock_registry = {"failing_dest": mock_dest}
        
        with patch('backend.routes.destinations.registry', mock_registry):
            # The function should propagate the exception
            with pytest.raises(Exception, match="Instantiation failed"):
                await list_destination_definitions()
    
    @pytest.mark.asyncio
    async def test_list_destination_definitions_config_schema_error(self):
        """Test when config_schema method fails"""
        mock_dest = MagicMock()
        mock_dest_instance = MagicMock()
        mock_dest_instance.config_schema.side_effect = Exception("Schema generation failed")
        mock_dest.return_value = mock_dest_instance
        
        mock_registry = {"schema_failing_dest": mock_dest}
        
        with patch('backend.routes.destinations.registry', mock_registry):
            # The function should propagate the exception
            with pytest.raises(Exception, match="Schema generation failed"):
                await list_destination_definitions()
    
    @pytest.mark.asyncio
    async def test_list_destination_definitions_mixed_success_and_failure(self):
        """Test with mix of working and failing destinations"""
        # Working destination
        mock_dest1 = MagicMock()
        mock_dest1_instance = MagicMock()
        mock_dest1_instance.config_schema.return_value = {"type": "object"}
        mock_dest1.return_value = mock_dest1_instance
        
        # Failing destination
        mock_dest2 = MagicMock()
        mock_dest2.side_effect = Exception("Failed to instantiate")
        
        mock_registry = {
            "working_dest": mock_dest1,
            "failing_dest": mock_dest2
        }
        
        with patch('backend.routes.destinations.registry', mock_registry):
            # Should fail on the first failing destination
            with pytest.raises(Exception, match="Failed to instantiate"):
                await list_destination_definitions()
    
    @pytest.mark.asyncio
    async def test_list_destination_definitions_return_type(self):
        """Test that the function returns the correct type"""
        mock_dest = MagicMock()
        mock_dest_instance = MagicMock()
        mock_dest_instance.config_schema.return_value = {"type": "object"}
        mock_dest.return_value = mock_dest_instance
        
        mock_registry = {"test_dest": mock_dest}
        
        with patch('backend.routes.destinations.registry', mock_registry):
            result = await list_destination_definitions()
        
        # Should return a list
        assert isinstance(result, list)
        # Each item should be a dict with 'name' and 'schema' keys
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert "name" in result[0]
        assert "schema" in result[0]
        assert result[0]["name"] == "test_dest"
        assert result[0]["schema"] == {"type": "object"}


class TestDestinationsRoutesEdgeCases:
    """Test edge cases for destinations routes"""
    
    @pytest.mark.asyncio
    async def test_destination_with_none_schema(self):
        """Test destination that returns None schema"""
        mock_dest = MagicMock()
        mock_dest_instance = MagicMock()
        mock_dest_instance.config_schema.return_value = None
        mock_dest.return_value = mock_dest_instance
        
        mock_registry = {"none_schema_dest": mock_dest}
        
        with patch('backend.routes.destinations.registry', mock_registry):
            result = await list_destination_definitions()
        
        assert len(result) == 1
        assert result[0]["name"] == "none_schema_dest"
        assert result[0]["schema"] is None
    
    @pytest.mark.asyncio
    async def test_destination_with_empty_schema(self):
        """Test destination that returns empty schema"""
        mock_dest = MagicMock()
        mock_dest_instance = MagicMock()
        mock_dest_instance.config_schema.return_value = {}
        mock_dest.return_value = mock_dest_instance
        
        mock_registry = {"empty_schema_dest": mock_dest}
        
        with patch('backend.routes.destinations.registry', mock_registry):
            result = await list_destination_definitions()
        
        assert len(result) == 1
        assert result[0]["name"] == "empty_schema_dest"
        assert result[0]["schema"] == {}
    
    @pytest.mark.asyncio
    async def test_destination_names_preserved(self):
        """Test that destination names are preserved exactly"""
        mock_dest = MagicMock()
        mock_dest_instance = MagicMock()
        mock_dest_instance.config_schema.return_value = {"type": "object"}
        mock_dest.return_value = mock_dest_instance
        
        # Test various name formats
        mock_registry = {
            "simple": mock_dest,
            "with-dashes": mock_dest,
            "with_underscores": mock_dest,
            "MixedCase": mock_dest,
            "123numeric": mock_dest
        }
        
        with patch('backend.routes.destinations.registry', mock_registry):
            result = await list_destination_definitions()
        
        assert len(result) == 5
        names = {item["name"] for item in result}
        expected_names = {"simple", "with-dashes", "with_underscores", "MixedCase", "123numeric"}
        assert names == expected_names
