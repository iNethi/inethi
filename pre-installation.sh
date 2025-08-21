#!/bin/bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

VENV_DIR="venv"

echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                    iNethi Pre-Installation                   ║${NC}"
echo -e "${CYAN}║                        Enhanced v1.1.0                       ║${NC}"
echo -e "${CYAN}║                                                              ║${NC}"
echo -e "${CYAN}║  Setting up Python, Ansible, and system dependencies...      ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo

echo -e "${BLUE}🔄 Updating system packages...${NC}"
sudo apt-get update
sudo apt-get upgrade

echo -e "${BLUE}⏳ Waiting for system updates to complete...${NC}"
sleep 2

echo -e "${CYAN}🐍 Checking Python 3 installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}⚠️  Python 3 is not installed. Installing now...${NC}"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [[ -n $(command -v apt-get) ]]; then
            sudo apt-get update
            sudo apt-get install -y python3
        else
            echo -e "${RED}❌ Package manager not found. Please install Python 3 manually.${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ Unsupported operating system: $OSTYPE${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Python 3 has been installed.${NC}"
else
    echo -e "${GREEN}✅ Python 3 is already installed.${NC}"
fi

echo -e "${CYAN}📦 Checking pip3 installation...${NC}"
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}⚠️  pip3 is not installed. Installing now...${NC}"

    if [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            if [ "$ID" == "ubuntu" ] || [ "$ID" == "debian" ]; then
                sudo apt-get update
                sudo apt-get install -y python3-pip
            else
                echo -e "${RED}❌ Your operating system is not supported by this script.${NC}"
                exit 1
            fi
        else
            echo -e "${RED}❌ Your operating system is not supported by this script.${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ Your operating system is not supported by this script.${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ pip3 has been installed.${NC}"
else
    echo -e "${GREEN}✅ pip3 is already installed.${NC}"
fi

echo -e "${CYAN}🔧 Checking Ansible installation...${NC}"
if ! command -v ansible &> /dev/null; then
    echo -e "${YELLOW}⚠️  Ansible is not installed. Installing now...${NC}"

    if [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            if [ "$ID" == "ubuntu" ] || [ "$ID" == "debian" ]; then
                sudo apt-get update
                sudo apt-get install -y ansible
            else
                echo -e "${RED}❌ Your operating system is not supported by this script.${NC}"
                exit 1
            fi
        else
            echo -e "${RED}❌ Your operating system is not supported by this script.${NC}"
                exit 1
        fi
    else
        echo -e "${RED}❌ Your operating system is not supported by this script.${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ Ansible has been installed.${NC}"
else
    echo -e "${GREEN}✅ Ansible is already installed.${NC}"
fi

echo -e "${CYAN}🔐 Checking OpenSSH server installation...${NC}"
if ! command -v sshd &> /dev/null; then
    echo -e "${YELLOW}⚠️  OpenSSH server is not installed. Installing...${NC}"

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get install openssh-server -y
        sudo apt-get install ssh -y
    fi

    echo -e "${GREEN}✅ OpenSSH server installed successfully.${NC}"
else
    echo -e "${GREEN}✅ OpenSSH server is already installed.${NC}"
fi

echo -e "${CYAN}🔑 Checking sshpass installation...${NC}"
if ! command -v sshpass &> /dev/null; then
    echo -e "${YELLOW}⚠️  sshpass is not installed. Installing now...${NC}"

    if [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            if [ "$ID" == "ubuntu" ] || [ "$ID" == "debian" ]; then
                sudo apt-get update
                sudo apt-get install -y sshpass
            else
                echo -e "${RED}❌ Your operating system is not supported by this script.${NC}"
                exit 1
            fi
        else
            echo -e "${RED}❌ Your operating system is not supported by this script.${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ Your operating system is not supported by this script.${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ sshpass has been installed.${NC}"
else
    echo -e "${GREEN}✅ sshpass is already installed.${NC}"
fi

echo -e "${CYAN}🐍 Installing Python virtual environment support...${NC}"
sudo apt install -y python3-venv

echo -e "${CYAN}📁 Setting up Python virtual environment...${NC}"
# Check if the virtual environment directory exists
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}⚠️  Creating new virtual environment...${NC}"
    # The virtual environment does not exist, create it
    python3 -m venv "$VENV_DIR" || exit 1

    # Activate the virtual environment
    source "$VENV_DIR/bin/activate" || exit 1

    # Install the requirements
    if [ -f "requirements.txt" ]; then
        echo -e "${BLUE}📦 Installing Python requirements...${NC}"
        pip3 install -r requirements.txt || exit 1
    else
        echo -e "${RED}❌ No requirements.txt file found.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Virtual environment already exists.${NC}"
    # The virtual environment exists, activate it
    source "$VENV_DIR/bin/activate" || exit 1
fi

echo -e "${BLUE}📦 Installing/Updating Python Requirements${NC}"
pip3 install -r requirements.txt || exit 1
echo

echo -e "${CYAN}🔧 Installing Ansible Galaxy requirements...${NC}"
ansible-galaxy collection install -r requirements.yml

echo -e "${CYAN}📝 Setting up configuration files...${NC}"

# Copy .env.example to .env if it doesn't exist
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ Created .env file from .env.example${NC}"
        echo -e "${BLUE}   Please edit .env file with your configuration values${NC}"
    else
        echo -e "${YELLOW}⚠️  Warning: .env.example not found${NC}"
    fi
else
    echo -e "${BLUE}ℹ️  .env file already exists${NC}"
fi

# Copy default_passwords.json.example to default_passwords.json if it doesn't exist
if [ ! -f "default_passwords.json" ]; then
    if [ -f "default_passwords.json.example" ]; then
        cp default_passwords.json.example default_passwords.json
        echo -e "${GREEN}✅ Created default_passwords.json from default_passwords.json.example${NC}"
        echo -e "${BLUE}   Please edit default_passwords.json with your custom passwords (optional)${NC}"
    else
        echo -e "${YELLOW}⚠️  Warning: default_passwords.json.example not found${NC}"
    fi
else
    echo -e "${BLUE}ℹ️  default_passwords.json file already exists${NC}"
fi

echo
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    🎉 Pre-installation Complete! 🎉          ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║  Next steps:                                                 ║${NC}"
echo -e "${GREEN}║  • Run: source venv/bin/activate                             ║${NC}"
echo -e "${GREEN}║  • Run: python3 main.py                                      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo
sleep 3