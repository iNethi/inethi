# iNethi Dev
This is the developer repo containing the latest work yet to be integrated into the main iNethi repo. Please use the [terminal-based iNethi repo](https://github.com/iNethi/inethi) or [GUI installer](https://github.com/iNethi/gui-installer) to build your iNethi instance. Alternatively to contribute to iNethi submit a PR here.

## Pre-installation
This repo makes use of Ansible and Python to install Docker containers. Please run the pre-installation script:
```
./preinstallation.sh
```
This should install Python 3, pip3, the Python requirements in the requirements.txt file, Ansible, OpenSSH server and sshpass.

## Installation
These steps should work on Ubuntu and Mac... if you encounter errors with the pre-installation steps please manually 
install the following on the machine you are running the Python script from:
` Python 3, pip3, the Python requirements in the requirements.txt file, Ansible, OpenSSH server and sshpass `.

To install: 
1. run the pre-installation script on your host machine:
```
./preinstallation.sh
```
2. Run the Python script and follow then on-screen prompts:
```
python3 main.py   
```

**remember to use pip3 and python3.**
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
