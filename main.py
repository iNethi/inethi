#!/usr/bin/env python3
"""
iNethi Platform Builder - Enhanced Python Application
====================================================

A modern, robust Python application for building iNethi platforms on remote servers.
Integrates with centralized configuration system and provides enhanced user experience.

Last Project Update: December 2024
Author(s): Keegan White <keeganthomaswhite@gmail.com>
Maintainer(s): Keegan White <keeganthomaswhite@gmail.com>
"""
import argparse
import pathlib
import sys
from typing import List, Optional, Dict, Any

from config import config
from utils.ansible_runner_utils import run_playbook
from utils.file_utils import (
    write_to_inventory,
    load_device_logins_from_yaml,
    save_device_login_to_yaml
)
from utils.log import Log
from utils.colors import Colors

# Import setup and validation functions
try:
    from setup_config import run_setup, run_vault_setup
    from validate_config import run_validation
except ImportError as e:
    print(f"Error importing setup/validation modules: {e}")
    print("Please ensure setup_config.py and validate_config.py are in the same directory")
    sys.exit(1)

# Constants
SAVED_DEVICES = pathlib.Path(__file__).parent / "saved-devices/saved-devices.yml"
INVENTORY_PATH = pathlib.Path(__file__).parent / "ansible/inventory/hosts"

# Available services
SERVICES = {
    'azuracast': 'Azuracast - Self-hosted web radio management',
    'dnsmasq': 'DNSMasq - DNS server',
    'jellyfin': 'Jellyfin - Media server',
    'keycloak': 'Keycloak - Identity and access management',
    'kiwix': 'Kiwix - Offline Wikipedia reader',
    'moodle': 'Moodle - Learning management system',
    'nextcloud': 'Nextcloud - File sharing, backups and collaboration',
    'radiusdesk': 'RADIUSdesk - Network management',
    'splash': 'Splash - Captive portal',
    'wordpress': 'WordPress - build your own website'
}

# Playbook paths
PLAYBOOKS = {
    'system-checks': 'ansible/system-checks.yml',
    'system-setup': 'ansible/system-setup.yml',
    'traefik': 'ansible/traefik.yml',
    **{service: f'ansible/{service}.yml' for service in SERVICES.keys()}
}


class INethiBuilder:
    """Main iNethi platform builder class"""

    def __init__(self, verbose=False):
        self.log = Log()
        self.colors = Colors()
        self.device_config: Optional[Dict[str, Any]] = None
        self.selected_services: List[str] = []
        self.verbose = verbose

    def print_banner(self):
        """Print application banner"""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║                    iNethi Platform Builder                   ║
║                        Enhanced v1.1.0                       ║
║                                                              ║
║  Self-hosted services for offline communities and networks   ║
╚══════════════════════════════════════════════════════════════╝
        """
        self.log.log(banner, 'SUCCESS')

    def check_and_setup_configuration(self) -> bool:
        """Check if configuration exists and offer to set it up"""
        # Ensure configuration files exist
        self._ensure_config_files()

        if not pathlib.Path('.env').exists():
            self.log.log("⚠️  No configuration found", 'WARNING')

            setup_choice = input("Would you like to set up your configuration now? (y/n): ").strip().lower()
            if setup_choice in ['y', 'yes']:
                self.log.log("🔧 Starting configuration setup...", 'INFO')
                if not run_setup():
                    self.log.log("❌ Configuration setup failed", 'ERROR')
                    return False
                self.log.log("✅ Configuration setup completed", 'SUCCESS')
            else:
                self.log.log("❌ Configuration setup required to continue", 'ERROR')
                return False
        else:
            # Configuration exists, check if vault needs setup
            vault_file = pathlib.Path("ansible/vault/production.yml")
            vault_password_file = pathlib.Path(".vault_password")

            needs_vault_setup = False
            if not vault_file.exists():
                needs_vault_setup = True
            elif not vault_password_file.exists():
                needs_vault_setup = True
            else:
                # Check if vault file is encrypted
                try:
                    with open(vault_file, 'r') as f:
                        content = f.read()
                        if not content.startswith('$ANSIBLE_VAULT'):
                            needs_vault_setup = True
                except Exception:
                    needs_vault_setup = True

            if needs_vault_setup:
                self.log.log("⚠️ Vault configuration incomplete", 'WARNING')
                vault_choice = input("Would you like to complete vault setup now? (y/n): ").strip().lower()
                if vault_choice in ['y', 'yes']:
                    self.log.log("🔧 Starting vault setup...", 'INFO')
                    if not run_vault_setup():
                        self.log.log("❌ Vault setup failed", 'ERROR')
                        return False
                    self.log.log("✅ Vault setup completed", 'SUCCESS')
                else:
                    self.log.log("❌ Vault setup required for production deployment", 'ERROR')
                    return False
            else:
                # Vault exists and is encrypted, ask if user wants to update
                self.log.log("ℹ️  Vault configuration exists", 'INFO')
                update_choice = input("Would you like to update vault passwords? (y/n): ").strip().lower()
                if update_choice in ['y', 'yes']:
                    self.log.log("🔧 Starting vault update...", 'INFO')
                    if not run_vault_setup():
                        self.log.log("❌ Vault update failed", 'ERROR')
                        return False
                    self.log.log("✅ Vault update completed", 'SUCCESS')
                else:
                    self.log.log("ℹ️  Vault configuration unchanged", 'INFO')

        return True

    def _ensure_config_files(self):
        """Ensure required configuration files exist"""
        # Check and copy .env.example to .env
        env_file = pathlib.Path('.env')
        env_example = pathlib.Path('.env.example')

        if not env_file.exists() and env_example.exists():
            try:
                import shutil
                shutil.copy2(env_example, env_file)
                self.log.log("✅ Created .env file from .env.example", 'SUCCESS')
                self.log.log("   Please edit .env file with your configuration values", 'INFO')
            except Exception as e:
                self.log.log(f"❌ Failed to create .env file: {e}", 'ERROR')

        # Check and copy default_passwords.json.example to default_passwords.json
        passwords_file = pathlib.Path('default_passwords.json')
        passwords_example = pathlib.Path('default_passwords.json.example')

        if not passwords_file.exists() and passwords_example.exists():
            try:
                import shutil
                shutil.copy2(passwords_example, passwords_file)
                self.log.log("✅ Created default_passwords.json from default_passwords.json.example", 'SUCCESS')
                self.log.log("   Please edit default_passwords.json with your custom passwords (optional)", 'INFO')
            except Exception as e:
                self.log.log(f"❌ Failed to create default_passwords.json: {e}", 'ERROR')

    def validate_environment(self) -> bool:
        """Validate the current environment setup"""
        self.log.log("🔍 Running configuration validation...", 'INFO')

        if not run_validation():
            self.log.log("❌ Configuration validation failed", 'ERROR')
            return False

        self.log.log("✅ Configuration validation passed", 'SUCCESS')
        return True

    def get_server_configuration(self) -> bool:
        """Get server configuration from user or saved devices"""
        self.log.log("🔧 Server Configuration", 'HEADING')

        # Check for saved devices
        if SAVED_DEVICES.exists():
            device_data = load_device_logins_from_yaml(str(SAVED_DEVICES))
            if device_data and device_data.get('login_details'):
                return self._select_saved_device(device_data['login_details'])

        # Get new server configuration
        return self._get_new_server_config()

    def _select_saved_device(self, devices: List[Dict[str, Any]]) -> bool:
        """Select from saved devices"""
        self.log.log("📋 Found saved server configurations:", 'INFO')

        for i, device in enumerate(devices, 1):
            auth_display = "🔑 Key" if device['auth_method'] == 'key' else "🔒 Password"
            print(f"  {i}) {device['name']} - {device['ip']} ({device['user']}) {auth_display}")

        print(f"  {len(devices) + 1}) Enter new server configuration")

        while True:
            try:
                choice = input("\nSelect server configuration: ").strip()
                choice_num = int(choice)

                if choice_num == len(devices) + 1:
                    return self._get_new_server_config()
                elif 1 <= choice_num <= len(devices):
                    self.device_config = devices[choice_num - 1]
                    self.log.log(f"✅ Selected: {self.device_config['name']}", 'SUCCESS')
                    return True
                else:
                    self.log.log("❌ Invalid selection", 'ERROR')
            except ValueError:
                self.log.log("❌ Please enter a valid number", 'ERROR')

    def _get_new_server_config(self) -> bool:
        """Get new server configuration from user"""
        self.log.log("📝 Enter server configuration:", 'INFO')

        # Get IP address
        ip = input("🌐 Server IP Address: ").strip()
        if not ip:
            self.log.log("❌ IP address is required", 'ERROR')
            return False

        # Get username
        user = input("👤 Username: ").strip()
        if not user:
            self.log.log("❌ Username is required", 'ERROR')
            return False

        # Get authentication method
        self.log.log("🔐 Authentication method:", 'INFO')
        print("  1) Password")
        print("  2) SSH Key")

        while True:
            auth_choice = input("Select method (1/2): ").strip()
            if auth_choice in ['1', '2']:
                auth_method = 'password' if auth_choice == '1' else 'key'
                break
            else:
                self.log.log("❌ Please select 1 or 2", 'ERROR')

        # Get authentication value
        if auth_method == 'password':
            auth_value = input("🔒 Password: ")
        else:
            auth_value = input("🔑 SSH Key path: ").strip()

        if not auth_value:
            self.log.log("❌ Authentication value is required", 'ERROR')
            return False

        # Create device config
        self.device_config = {
            'ip': ip,
            'user': user,
            'auth_method': auth_method,
            'auth_value': auth_value
        }

        # Ask to save configuration
        save = input("\n💾 Save this configuration for future use? (y/n): ").strip().lower()
        if save in ['y', 'yes']:
            name = input("📝 Configuration name: ").strip()
            if name:
                save_device_login_to_yaml(
                    str(SAVED_DEVICES), name, ip, user, auth_method, auth_value
                )
                self.device_config['name'] = name
                self.log.log("✅ Configuration saved", 'SUCCESS')

        return True

    def select_services(self) -> bool:
        """Select services to install"""
        self.log.log("📦 Service Selection", 'HEADING')
        self.log.log("Available services:", 'INFO')

        for i, (service, description) in enumerate(SERVICES.items(), 1):
            print(f"  {i:2d}) {service:12} - {description}")

        # Add "Select All" option
        all_option_num = len(SERVICES) + 1
        print(f"  {all_option_num:2d}) all           - Install all services")

        self.log.log("\n💡 Tip: You can select multiple services separated by commas, or 'all' for everything", 'INFO')

        while True:
            try:
                selection = input("\nSelect services to install: ").strip()
                if not selection:
                    self.log.log("❌ Please select at least one service", 'ERROR')
                    continue

                # Check for "all" option
                if selection.lower() == 'all':
                    self.selected_services = list(SERVICES.keys())
                else:
                    # Parse selection
                    selected_indices = [int(idx.strip()) - 1 for idx in selection.split(',')]
                    self.selected_services = [list(SERVICES.keys())[idx] for idx in selected_indices]

                # Validate selection
                if not self.selected_services:
                    self.log.log("❌ No valid services selected", 'ERROR')
                    continue

                # Confirm selection
                self.log.log("Selected services:", 'INFO')
                for service in self.selected_services:
                    print(f"  ✅ {service} - {SERVICES[service]}")

                confirm = input("\nProceed with installation? (y/n): ").strip().lower()
                if confirm in ['y', 'yes']:
                    return True
                else:
                    self.selected_services = []

            except (ValueError, IndexError):
                self.log.log("❌ Invalid selection. Please enter valid service numbers or 'all'", 'ERROR')

    def setup_system(self) -> bool:
        """Setup system prerequisites"""
        self.log.log("🔧 System Setup", 'HEADING')

        # Check if setup should be skipped
        skip_setup = input("Skip system setup? (y/n): ").strip().lower()
        if skip_setup in ['y', 'yes']:
            self.log.log("⏭️  Skipping system setup", 'INFO')
            return True

        # Run system checks
        self.log.log("🔍 Running system checks...", 'INFO')
        if not self._run_playbook('system-checks'):
            self.log.log("❌ System checks failed", 'ERROR')
            return False

        # Install Docker and system requirements
        self.log.log("🐳 Installing Docker and system requirements...", 'INFO')
        if not self._run_playbook('system-setup'):
            self.log.log("❌ System setup failed", 'ERROR')
            return False

        # Setup Traefik (reverse proxy)
        self.log.log("🌐 Setting up Traefik reverse proxy...", 'INFO')
        if not self._run_playbook('traefik'):
            self.log.log("❌ Traefik setup failed", 'ERROR')
            return False

        self.log.log("✅ System setup completed successfully", 'SUCCESS')
        self.log.log("🌐 Access points:", 'INFO')
        self.log.log("   • Grafana: grafana.inethilocal.net", 'INFO')
        self.log.log("   • Prometheus: prometheus.inethilocal.net", 'INFO')
        self.log.log("   • Traefik: traefik.inethilocal.net", 'INFO')

        return True

    def install_services(self) -> bool:
        """Install selected services"""
        self.log.log("📦 Service Installation", 'HEADING')

        for i, service in enumerate(self.selected_services, 1):
            self.log.log(f"Installing {service} ({i}/{len(self.selected_services)})...", 'INFO')

            if not self._run_playbook(service):
                self.log.log(f"❌ Failed to install {service}", 'ERROR')
                return False

            self.log.log(f"○ {service} installed successfully", 'SUCCESS')

        return True

    def _run_playbook(self, playbook_name: str) -> bool:
        """Run an Ansible playbook"""
        playbook_path = PLAYBOOKS.get(playbook_name)
        if not playbook_path:
            self.log.log(f"❌ Playbook not found: {playbook_name}", 'ERROR')
            return False

        # Ensure inventory is written
        if not self._write_inventory():
            return False

        # Run playbook
        result = run_playbook(playbook_path, str(INVENTORY_PATH), self.verbose)
        return result == 0

    def _write_inventory(self) -> bool:
        """Write Ansible inventory file"""
        if not self.device_config:
            self.log.log("❌ No device configuration available", 'ERROR')
            return False

        try:
            write_to_inventory(
                self.device_config['ip'],
                self.device_config['user'],
                self.device_config['auth_method'],
                self.device_config['auth_value'],
                str(INVENTORY_PATH)
            )
            return True
        except Exception as e:
            self.log.log(f"❌ Failed to write inventory: {e}", 'ERROR')
            return False

    def run(self, services: Optional[List[str]] = None,
            skip_setup: bool = False, non_interactive: bool = False) -> bool:
        """Main execution method"""
        try:
            # Print banner
            self.print_banner()

            # Check and setup configuration if needed
            if not self.check_and_setup_configuration():
                return False

            # Validate environment
            if not self.validate_environment():
                self.log.log("❌ Configuration validation failed", 'ERROR')
                self.log.log("Please complete the configuration setup before proceeding", 'INFO')

                # Offer to run setup again
                setup_choice = input("Would you like to set up your configuration now? (y/n): ").strip().lower()
                if setup_choice in ['y', 'yes']:
                    self.log.log("🔧 Starting configuration setup...", 'INFO')
                    if not run_setup():
                        self.log.log("❌ Configuration setup failed", 'ERROR')
                        return False
                    self.log.log("✅ Configuration setup completed", 'SUCCESS')

                    # Validate again after setup
                    if not self.validate_environment():
                        self.log.log("❌ Configuration still invalid after setup", 'ERROR')
                        return False
                else:
                    self.log.log("❌ Configuration setup required to continue", 'ERROR')
                    return False

            # Non-interactive mode
            if non_interactive:
                return self._run_non_interactive(services, skip_setup)

            # Interactive mode
            return self._run_interactive(services, skip_setup)

        except KeyboardInterrupt:
            self.log.log("\n⚠️  Installation interrupted by user", 'WARNING')
            return False
        except Exception as e:
            self.log.log(f"❌ Unexpected error: {e}", 'ERROR')
            return False

    def _run_interactive(self, services: Optional[List[str]], skip_setup: bool) -> bool:
        """Run in interactive mode"""
        # Get server configuration
        if not self.get_server_configuration():
            return False

        # Select services
        if services:
            self.selected_services = services
        else:
            if not self.select_services():
                return False

        # Setup system
        if not skip_setup:
            if not self.setup_system():
                return False

        # Install services
        if not self.install_services():
            return False

        # Success
        self.log.log("→ Installation completed successfully!", 'SUCCESS')
        self.log.log("Your iNethi platform is now ready to use.", 'INFO')
        return True

    def _run_non_interactive(self, services: Optional[List[str]], skip_setup: bool) -> bool:
        """Run in non-interactive mode"""
        # Use configuration from .env file
        server_config = config.get_server_config()
        if not server_config.ip or not server_config.auth_value:
            self.log.log("❌ Server configuration incomplete in .env file", 'ERROR')
            return False

        self.device_config = {
            'ip': server_config.ip,
            'user': server_config.user,
            'auth_method': server_config.auth_method,
            'auth_value': server_config.auth_value
        }

        # Use provided services or defaults
        if services:
            self.selected_services = services
        else:
            self.selected_services = config.get_default_services()

        # Setup system
        if not skip_setup:
            if not self.setup_system():
                return False

        # Install services
        if not self.install_services():
            return False

        self.log.log("🎉 Non-interactive installation completed!", 'SUCCESS')
        return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="iNethi Platform Builder - Enhanced Python Application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Interactive mode
  %(prog)s --services nextcloud,jellyfin  # Install specific services
  %(prog)s --services all     # Install all services
  %(prog)s --non-interactive  # Use .env configuration
  %(prog)s --skip-setup       # Skip system setup
  %(prog)s --verbose          # Show verbose Ansible output
        """
    )

    parser.add_argument(
        '--services',
        help='Comma-separated list of services to install'
    )
    parser.add_argument(
        '--skip-setup',
        action='store_true',
        help='Skip system setup (Docker, Traefik, etc.)'
    )
    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='Run in non-interactive mode using .env configuration'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show verbose Ansible output'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='iNethi Platform Builder v2.0'
    )

    args = parser.parse_args()

    # Parse services
    services = None
    if args.services:
        if args.services.lower() == 'all':
            services = list(SERVICES.keys())
        else:
            services = [s.strip() for s in args.services.split(',')]
            # Validate services
            invalid_services = [s for s in services if s not in SERVICES]
            if invalid_services:
                print(f"❌ Invalid services: {', '.join(invalid_services)}")
                print(f"Available services: {', '.join(SERVICES.keys())}")
                sys.exit(1)

    # Run builder
    builder = INethiBuilder(verbose=args.verbose)
    success = builder.run(
        services=services,
        skip_setup=args.skip_setup,
        non_interactive=args.non_interactive
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
