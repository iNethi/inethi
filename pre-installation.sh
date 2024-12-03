#!/bin/bash
VENV_DIR="venv"

echo "Starting installation of Python 3, pip3, the Python requirements in the requirements.txt file, Ansible, the Ansible
requirements in the requirements.yml file, OpenSSH server and sshpass"
echo

sudo apt-get update
sudo apt-get upgrade


sleep 2
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Installing now..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [[ -n $(command -v apt-get) ]]; then
            sudo apt-get update
            sudo apt-get install -y python3
        else
            echo "Package manager not found. Please install Python 3 manually."
            exit 1
        fi
    else
        echo "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    echo "Python 3 has been installed."
else
    echo "Python 3 is already installed."
fi

if ! command -v pip3 &> /dev/null; then
    echo "pip3 is not installed. Installing now..."

    if [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            if [ "$ID" == "ubuntu" ] || [ "$ID" == "debian" ]; then
                sudo apt-get update
                sudo apt-get install -y python3-pip
            else
                echo "Your operating system is not supported by this script."
                exit 1
            fi
        else
            echo "Your operating system is not supported by this script."
            exit 1
        fi
    else
        echo "Your operating system is not supported by this script."
        exit 1
    fi

    echo "pip3 has been installed."
else
    echo "pip3 is already installed."
fi

if ! command -v ansible &> /dev/null; then
    echo "Ansible is not installed. Installing now..."

    if [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            if [ "$ID" == "ubuntu" ] || [ "$ID" == "debian" ]; then
                sudo apt-get update
                sudo apt-get install -y ansible
            else
                echo "Your operating system is not supported by this script."
                exit 1
            fi
        else
            echo "Your operating system is not supported by this script."
            exit 1
        fi
    else
        echo "Your operating system is not supported by this script."
        exit 1
    fi

    echo "Ansible has been installed."
else
    echo "Ansible is already installed."
fi

if ! command -v sshd &> /dev/null; then
    echo "OpenSSH server is not installed. Installing..."

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get install openssh-server -y
        sudo apt-get install ssh -y
    fi

    echo "OpenSSH server installed successfully."
else
    echo "OpenSSH server is already installed."
fi

if ! command -v sshpass &> /dev/null; then
    echo "sshpass is not installed. Installing now..."

    if [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            if [ "$ID" == "ubuntu" ] || [ "$ID" == "debian" ]; then
                sudo apt-get update
                sudo apt-get install -y sshpass
            else
                echo "Your operating system is not supported by this script."
                exit 1
            fi
        else
            echo "Your operating system is not supported by this script."
            exit 1
        fi
    else
        echo "Your operating system is not supported by this script."
        exit 1
    fi

    echo "sshpass has been installed."
else
    echo "sshpass is already installed."
fi

sudo apt install -y python3-venv

# Check if the virtual environment directory exists
if [ ! -d "$VENV_DIR" ]; then
    # The virtual environment does not exist, create it
    python3 -m venv "$VENV_DIR" || exit 1

    # Activate the virtual environment
    source "$VENV_DIR/bin/activate" || exit 1

    # Install the requirements
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt || exit 1
    else
        echo "No requirements.txt file found."
        exit 1
    fi
else
    # The virtual environment exists, activate it
    source "$VENV_DIR/bin/activate" || exit 1
fi

echo "Installing Python Requirements"
pip3 install -r requirements.txt || exit 1
echo

echo "Installing ansible galaxy requirements"
ansible-galaxy collection install -r requirements.yml

echo "Pre-installation complete..."
sleep 3