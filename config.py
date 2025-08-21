"""
Configuration management for iNethi platform
Handles environment variables, configuration validation, and defaults
"""
import os
import pathlib
from typing import Dict, Any, Optional
from dataclasses import dataclass
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class ServerConfig:
    """Server configuration settings"""
    ip: str
    user: str
    auth_method: str
    auth_value: str


@dataclass
class EnvironmentConfig:
    """Environment-specific configuration"""
    environment: str
    data_mount: str
    domain: str
    bridge: str
    timezone: str
    log_level: str
    enable_debug: bool
    skip_ssl_verification: bool


class ConfigManager:
    """Centralized configuration management"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or pathlib.Path(__file__).parent / "config"
        self._config_cache: Dict[str, Any] = {}
        
    def get_environment(self) -> str:
        """Get current environment"""
        return os.getenv('ENVIRONMENT', 'production')
    
    def get_server_config(self) -> ServerConfig:
        """Get server configuration from environment variables"""
        return ServerConfig(
            ip=os.getenv('DEFAULT_SERVER_IP', ''),
            user=os.getenv('DEFAULT_SERVER_USER', 'ubuntu'),
            auth_method=os.getenv('DEFAULT_AUTH_METHOD', 'password'),
            auth_value=os.getenv('DEFAULT_AUTH_VALUE', '')
        )
    
    def get_environment_config(self) -> EnvironmentConfig:
        """Get environment-specific configuration"""
        env = self.get_environment()
        return EnvironmentConfig(
            environment=env,
            data_mount=os.getenv('DATA_MOUNT', '/mnt/data'),
            domain=os.getenv('INETHI_LOCAL_DOMAIN', 'inethilocal.net'),
            bridge=os.getenv('DOCKER_BRIDGE', 'inethi-bridge-traefik'),
            timezone=os.getenv('TIMEZONE', 'Africa/Johannesburg'),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            enable_debug=os.getenv('ENABLE_DEBUG_MODE', 'false').lower() == 'true',
            skip_ssl_verification=os.getenv('SKIP_SSL_VERIFICATION', 'false').lower() == 'true'
        )
    
    def get_default_services(self) -> list:
        """Get default services to install"""
        services_str = os.getenv('DEFAULT_SERVICES', 'traefik')
        return [s.strip() for s in services_str.split(',')]
    
    def get_ansible_config(self) -> Dict[str, str]:
        """Get Ansible-specific configuration"""
        return {
            'vault_password_file': os.getenv('ANSIBLE_VAULT_PASSWORD_FILE', '.vault_password'),
            'config_file': os.getenv('ANSIBLE_CONFIG', 'ansible/ansible.cfg'),
            'inventory_path': 'ansible/inventory/hosts'
        }
    
    def validate_config(self) -> bool:
        """Validate configuration settings"""
        errors = []
        
        # Validate environment
        env = self.get_environment()
        if env not in ['production']:
            errors.append(f"Invalid environment: {env}. Only 'production' is supported.")
        
        # Validate server config
        server_config = self.get_server_config()
        if not server_config.ip:
            errors.append("Server IP address is required")
        if not server_config.user:
            errors.append("Server user is required")
        if server_config.auth_method not in ['password', 'key']:
            errors.append("Auth method must be 'password' or 'key'")
        if not server_config.auth_value:
            errors.append("Auth value is required")
        
        # Validate paths
        env_config = self.get_environment_config()
        if not env_config.data_mount:
            errors.append("Data mount path is required")
        
        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        return True
    
    def validate_config_for_setup(self) -> bool:
        """Validate configuration settings for initial setup (more lenient)"""
        errors = []
        
        # Validate environment
        env = self.get_environment()
        if env not in ['production']:
            errors.append(f"Invalid environment: {env}. Only 'production' is supported.")
        
        # For setup, we don't require server config to be complete yet
        # as it will be collected during the interactive setup
        
        # Validate paths
        env_config = self.get_environment_config()
        if not env_config.data_mount:
            errors.append("Data mount path is required")
        
        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        return True
    
    def get_ansible_group_vars_path(self) -> str:
        """Get path to Ansible group vars for current environment"""
        env = self.get_environment()
        return f"ansible/group_vars/{env}.yml"
    
    def create_env_file(self, template_path: str = ".env.example") -> bool:
        """Create .env file from template if it doesn't exist"""
        env_file = pathlib.Path(".env")
        template_file = pathlib.Path(template_path)
        
        if env_file.exists():
            print(".env file already exists")
            return True
        
        if not template_file.exists():
            print(f"Template file {template_path} not found")
            return False
        
        try:
            with open(template_file, 'r') as f:
                content = f.read()
            
            with open(env_file, 'w') as f:
                f.write(content)
            
            print(f"Created .env file from {template_path}")
            print("Please edit .env file with your configuration values")
            return True
        except Exception as e:
            print(f"Error creating .env file: {e}")
            return False
    
    def load_yaml_config(self, file_path: str) -> Dict[str, Any]:
        """Load YAML configuration file"""
        if file_path in self._config_cache:
            return self._config_cache[file_path]
        
        try:
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)
                self._config_cache[file_path] = config
                return config
        except Exception as e:
            print(f"Error loading config file {file_path}: {e}")
            return {}


# Global configuration instance
config = ConfigManager()
