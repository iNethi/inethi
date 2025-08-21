# iNethi Platform Builder

## Overview

The **iNethi Platform** is a comprehensive, self-hosted solution for creating offline digital communities and local networks. It provides a complete ecosystem of services that can be deployed on a single Ubuntu server and accessed over a Local Area Network (LAN).

### What It Provides

- **Media Services**: Jellyfin for movies, music, and photos
- **File Sharing**: Nextcloud for file storage and collaboration
- **Learning**: Moodle for educational content and courses
- **Web Publishing**: WordPress for websites and blogs
- **Identity Management**: Keycloak for user authentication
- **Network Management**: RADIUSdesk for network access control
- **Offline Content**: Kiwix for offline Wikipedia and educational resources
- **Internet Radio**: Azuracast for broadcasting
- **Reverse Proxy**: Traefik for SSL termination and service routing

### Key Features

- **Offline-First**: All services work without internet connectivity
- **Docker-Based**: Containerized services for easy deployment and management
- **Centralized Management**: Single interface for all services
- **Production-Ready**: Secure, scalable, and maintainable
- **Community-Focused**: Designed for schools, libraries, community centers, and remote areas

## Setup

### System Requirements

- **Host Machine**: Ubuntu (recommended) or any Linux with Python 3
- **Target Server**: Ubuntu server with SSH access
- **Network**: Both machines on same LAN or accessible network

### Important Files

#### Configuration Files

- **`.env.example`** → **`.env`** - Main configuration template
- **`default_passwords.json.example`** → **`default_passwords.json`** - Service password templates
- **`ansible/group_vars/all.yml`** - Centralized Ansible variables
- **`ansible/vault/production.yml`** - Encrypted sensitive data (created during setup)

#### Core Scripts

- **`pre-installation.sh`** - Installs Python, Ansible, and dependencies
- **`main.py`** - Main deployment orchestrator
- **`setup_config.py`** - Interactive configuration setup
- **`validate_config.py`** - Configuration validation

#### Ansible Structure

- **`ansible/*.yml`** - Service deployment playbooks
- **`ansible/roles/*/`** - Individual service configurations
- **`ansible/ansible.cfg`** - Ansible configuration

### Initial Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/iNethi/inethi.git
   cd inethi
   ```

2. **Run pre-installation**:

   ```bash
   ./pre-installation.sh
   ```

   This script:

   - Installs Python 3, pip3, Ansible, SSH tools
   - Creates Python virtual environment
   - Installs required packages
   - Copies configuration templates

3. **Activate virtual environment**:
   ```bash
   source venv/bin/activate
   ```

## Running

### Interactive Deployment (Recommended)

```bash
python3 main.py
```

This will:

1. **Check configuration** - Ensure all required files exist
2. **Setup vault** - Create encrypted password storage
3. **Validate environment** - Check all prerequisites
4. **Server configuration** - Collect server details (IP, user, password)
5. **Service selection** - Choose which services to deploy
6. **System setup** - Install Docker, Traefik, and prerequisites
7. **Service deployment** - Deploy selected services

### Command Line Options

```bash
# Deploy specific services
python3 main.py --services nextcloud,jellyfin

# Deploy all services
python3 main.py --services all

# Skip system setup (Docker, Traefik)
python3 main.py --skip-setup

# Non-interactive mode (uses .env configuration)
python3 main.py --non-interactive

# Verbose output
python3 main.py --verbose
```

### What You Can Edit

#### Before Deployment

- **`.env`** - Server connection details, data mount location, domain
- **`default_passwords.json`** - Service passwords (optional, can use defaults)

#### After Deployment

- **`ansible/group_vars/all.yml`** - Service configurations, ports, settings
- **`ansible/vault/production.yml`** - Encrypted passwords (use `ansible-vault edit`)

#### Service-Specific

- **`ansible/roles/*/defaults/main.yml`** - Individual service settings
- **`ansible/roles/*/files/`** - Service configuration files

### Configuration Examples

#### Basic .env Configuration

```bash
# Server Configuration
DEFAULT_SERVER_IP=192.168.1.100
DEFAULT_SERVER_USER=ubuntu
DEFAULT_AUTH_METHOD=password
DEFAULT_AUTH_VALUE=your_server_password

# Storage
DATA_MOUNT=/mnt/data

# Domain
INETHI_LOCAL_DOMAIN=inethilocal.net
```

#### Service Selection

```bash
# Deploy core services only
DEFAULT_SERVICES=traefik,keycloak,nextcloud

# Deploy everything
DEFAULT_SERVICES=all
```

## Accessing Services

After deployment, services are available at:

- **Traefik Dashboard**: `https://traefik.inethilocal.net`
- **Nextcloud**: `https://nextcloud.inethilocal.net`
- **Jellyfin**: `https://jellyfin.inethilocal.net`
- **Moodle**: `https://moodle.inethilocal.net`
- **WordPress**: `https://wordpress.inethilocal.net`

### Network Configuration

To access services from other devices on your LAN:

1. **DNS Configuration**: Add `*.inethilocal.net` entries pointing to your server IP
2. **Firewall**: Ensure ports 80 and 443 are open on the server
3. **SSL Certificates**: Automatically generated by Traefik

## Documentation

- **[Services Overview](SERVICES.md)** - Information about available services
