# iNethi
This repo contains code you can use to set up an iNethi docker network. This is intended for Ubuntu x86 architecture.
Alternatively you can use our GUI installer [here](https://github.com/iNethi/gui-installer).

## Pre-installation
This repo makes use of Ansible and Python to install Docker containers. Please run the pre-installation script:
```
./preinstallation.sh
```
This should install Python 3, pip3, python ansible runner, Ansible, OpenSSH server and sshpass.

## Installation
These steps should work on Ubuntu and Mac... if you encounter errors with the pre-installation steps please manually 
install the following on the machine you are running the Python script from:
` Python 3, pip3, the Python requirements in the requirements.txt file, Ansible, the Ansible Community collection using 
ansilbe galaxy OpenSSH server and sshpass `.

To install: 
1. run the pre-installation script on your host machine:
```
./preinstallation.sh
```
2. Run the Python script and follow then on-screen prompts:
```
python3 main.py   
```

## Post Installation
### Defaults
- Usernames: `inethi`
- Passwords: `iNethi2023#`
- Mounted folders: `/mnt/data/*`
### Post Installation Instructions
Navigate [here](./configuring-services/README.md) in the repo to find out details on how to configure your iNethi 
instance.

## Testing a New Playbook
To test a new playbook you want to add you can run `python3 test_playbook.py`. However, **you need to have run the full
installation process at least once and edit the .env file**. Your username, IP address and password must be added to the
.env file
