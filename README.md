# iNethi Builder

## What is the iNethi Platform
This repo contains code to set up an iNethi system, but what is the iNethi system? The iNethi platform is a dockerised 
system that allows you to create locally-hosted services that are accessible of a Local Area Network (LAN). These 
services offer content delivery platforms like [Jellyfin](https://jellyfin.org/), accounting and user management systems 
like [RADIUSdesk](https://www.radiusdesk.com/) and our own [bespoke](https://github.com/iNethi/backend/tree/main) 
systems. You can find out more about the services offered [here](SERVICES.md).

## Running the Code
This code is intended to be **run on an Ubuntu machine** with the target system being **an Ubuntu server**. It is 
possible to install the required packages and run the code on non-ubuntu machines but the target system will always
need to be an Ubuntu machine.

### Pre-requisites
Before running the code install the required packages by running the [pre-installation script](pre-installation.sh):
`./pre-installation` from the root of the repo.

## Quickstart
Install the pre-requisites, activate the virtual environment created by the pre-install script and then run the Python 
script in the root of the repo:
1. `./pre-installation` 
2. `source venv/bin/activate`
3. `python3 main.py`

## Customisation
The current system uses Traefik and the `inethilocal.net` domain that we allow public LAN usage of to create a reverse
proxy that allows you to access the dockerised services. However, if you want to use your own certificate, change any 
usernames, passwords, data mounts etc. you can edit them in the ansible defaults folders in each directory. **PLEASE note**
to ensure the correct outcomes please change the *DATA_MOUNT* variable in all directories if you want to change it.

### Caveats
If you change your certificate or any variables relating the [keycloak service](ansible/roles/keycloak) ensure you 
change the necessary variables in the [certificate manager](ansible/roles/cert) as you will need to update your
keystore and certificates mounted to the Traefik and Keycloak containers to ensure encryption is upheld.

## Production
In a production environment please change all usernames and passwords. These can be found in the `defaults/main.yml` file
of each ansible role. Not all services require usernames and passwords.

The typical folder structure is as follows:
```
inethi-internal/
├── ansible/
│   ├── kiwix.yml
│   ├── roles/
│   │   ├── kiwix/
│   │   │   ├── defaults/
│   │   │   │   └── main.yml
│   │   │   └── files/
│   │   │   └── tasks/
```

## Accessing the Services
Root your LAN traffic to the server running the iNethi system using your hosts file or a firewall. Traefik is used as a
reverse-proxy so routing to the services is managed by it. Find the default URLs in the [services](SERVICES.md) file.