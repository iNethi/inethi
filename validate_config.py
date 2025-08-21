#!/usr/bin/env python3
"""
Configuration validation script for iNethi platform
Validates environment variables, Ansible configuration, and vault setup
"""
import sys
import pathlib
from config import config
from utils.log import Log
from utils.colors import (
    print_header, print_section, print_success, print_error, 
    print_warning, print_info, print_progress, separator
)

def validate_environment_setup():
    """Validate environment setup"""
    print_progress("Validating environment setup...")
    
    # Check if .env file exists
    env_file = pathlib.Path(".env")
    if not env_file.exists():
        print_warning("No .env file found. Creating from template...")
        if not config.create_env_file():
            print_error("Failed to create .env file")
            return False
        print_warning("Please edit .env file with your configuration and run validation again")
        return False
    
    # Validate configuration (use lenient validation for setup)
    if not config.validate_config_for_setup():
        print_error("Configuration validation failed")
        print_info("Please complete the configuration setup before proceeding")
        return False
    
    print_success("Environment setup validation passed")
    return True

def validate_ansible_setup():
    """Validate Ansible setup"""
    print_progress("Validating Ansible setup...")
    
    # Check Ansible configuration
    ansible_config = config.get_ansible_config()
    config_file = pathlib.Path(ansible_config['config_file'])
    
    if not config_file.exists():
        print_error(f"Ansible config file not found: {config_file}")
        return False
    
    # Check inventory directory
    inventory_dir = pathlib.Path("ansible/inventory")
    if not inventory_dir.exists():
        print_error("Ansible inventory directory not found")
        return False
    
    # Check group_vars directory
    group_vars_dir = pathlib.Path("ansible/group_vars")
    if not group_vars_dir.exists():
        print_error("Ansible group_vars directory not found")
        return False
    
    # Check for all.yml (global variables)
    all_group_vars = group_vars_dir / "all.yml"
    if not all_group_vars.exists():
        print_error("Global group_vars file not found: ansible/group_vars/all.yml")
        return False
    
    # For production environment, we use vault files instead of environment-specific group_vars
    env = config.get_environment()
    if env == 'production':
        print_success("Production environment detected - using vault files for secrets")
    
    print_success("Ansible setup validation passed")
    return True

def validate_vault_setup():
    """Validate Ansible vault setup"""
    print_progress("Validating Ansible vault setup...")
    
    env = config.get_environment()
    
    # Only production environment is supported
    if env != 'production':
        print_error(f"Only production environment is supported. Current environment: {env}")
        return False
    
    # For production, vault files are required
    vault_file = pathlib.Path("ansible/vault/production.yml")
    if not vault_file.exists():
        print_warning("Production vault file not found")
        print_info("This will be created during the setup process")
        return True  # Allow setup to continue, vault will be created
    
    # Check if vault file is encrypted
    try:
        with open(vault_file, 'r') as f:
            content = f.read()
            if not content.startswith('$ANSIBLE_VAULT'):
                print_warning("Production vault file exists but is not encrypted")
                print_info("This will be encrypted during the setup process")
                return True  # Allow setup to continue, vault will be encrypted
    except Exception as e:
        print_warning(f"Error reading vault file: {e}")
        print_info("This will be fixed during the setup process")
        return True  # Allow setup to continue
    
    print_success("Vault setup validation passed")
    return True

def validate_roles_setup():
    """Validate Ansible roles setup"""
    print_progress("Validating Ansible roles setup...")
    
    roles_dir = pathlib.Path("ansible/roles")
    if not roles_dir.exists():
        print_error("Ansible roles directory not found")
        return False
    
    # Check for required roles
    required_roles = [
        'docker', 'traefik', 'nextcloud', 'jellyfin', 'keycloak',
        'moodle', 'wordpress', 'kiwix', 'radiusdesk', 'azuracast',
        'dnsmasq', 'splash', 'cert', 'folders'
    ]
    
    missing_roles = []
    for role in required_roles:
        role_dir = roles_dir / role
        if not role_dir.exists():
            missing_roles.append(role)
    
    if missing_roles:
        print_error(f"Missing required roles: {', '.join(missing_roles)}")
        return False
    
    print_success("Roles setup validation passed")
    return True

def run_validation() -> bool:
    """Run the complete validation process"""
    print_header("iNethi Configuration Validation", "Validating your setup for production deployment")
    
    # Run all validations
    validations = [
        ("Environment Setup", validate_environment_setup),
        ("Ansible Setup", validate_ansible_setup),
        ("Vault Setup", validate_vault_setup),
        ("Roles Setup", validate_roles_setup)
    ]
    
    all_passed = True
    for name, validation_func in validations:
        print_section(name)
        if not validation_func():
            all_passed = False
    
    if all_passed:
        print_success("🎉 Your configuration is ready for production deployment!")
        return True
    else:
        print_warning("⚠️  Some configuration issues detected")
        print_info("The interactive setup will help you fix these issues")
        return False  # Don't allow setup to continue with validation errors

def main():
    """Main validation function"""
    success = run_validation()
    
    if success:
        print_header("All Validations Passed!", "Your iNethi configuration is ready for deployment")
        return 0
    else:
        print_header("Some Validations Failed", "Please fix the issues above before proceeding")
        return 1

if __name__ == "__main__":
    sys.exit(main())
