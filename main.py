"""
Entry point for the iNethi builder using ansible and
python to build a remote server.
Last Project Update: December 2, 2024
Author(s): Keegan White <keeganthomaswhite@gmail.com>
Maintainer(s): Keegan White <keeganthomaswhite@gmail.com>
"""
import pathlib

from utils.ansible_runner_utils import run_playbook
from utils.file_utils import (
    write_to_inventory,
    load_device_logins_from_yaml,
    save_device_login_to_yaml
)
from utils.log import Log

abs_path_parent = pathlib.Path(__file__).parent.resolve()

# define constants for playbooks
SERVER_CHOICES = [
    'azuracast',
    'dnsmasq',
    'jellyfin',
    'keycloak',
    'kiwix',
    'moodle',
    'nextcloud',
    'radiusdesk',
    'splash',
    'wordpress'
]

AZURACAST = f'{abs_path_parent}/ansible/azuracast.yml'
DNSMASQ = f'{abs_path_parent}/ansible/dnsmasq.yml'
JELLYFIN = f'{abs_path_parent}/ansible/jellyfin.yml'
KEYCLOAK = f'{abs_path_parent}/ansible/keycloak.yml'
KIWIX = f'{abs_path_parent}/ansible/kiwix.yml'
MOODLE = f'{abs_path_parent}/ansible/moodle.yml'
NEXTCLOUD = f'{abs_path_parent}/ansible/nextcloud.yml'
RADIUSDESK = f'{abs_path_parent}/ansible/radiusdesk.yml'
SPLASH = f'{abs_path_parent}/ansible/splash.yml'
SYSTEM_CHECKS = f'{abs_path_parent}/ansible/system-checks.yml'
SYSTEM_SETUP = f'{abs_path_parent}/ansible/system-setup.yml'
TRAEFIK = f'{abs_path_parent}/ansible/traefik.yml'
WORDPRESS = f'{abs_path_parent}/ansible/wordpress.yml'

# dict for mapping

service_map = {
    'azuracast': AZURACAST,
    'dnsmasq': DNSMASQ,
    'jellyfin': JELLYFIN,
    'keycloak': KEYCLOAK,
    'kiwix': KIWIX,
    'moodle': MOODLE,
    'nextcloud': NEXTCLOUD,
    'radiusdesk': RADIUSDESK,
    'splash': SPLASH,
    'wordpress': WORDPRESS
}

# define constants for files
SAVED_DEVICES = f'{abs_path_parent}/saved-devices/saved-devices.yml'
INVENTORY_PATH = f'{abs_path_parent}/ansible/inventory/hosts'

# define constants for logging
WARNING = 'WARNING'
SUCCESS = 'SUCCESS'
ERROR = 'ERROR'
HEADING = 'HEADING'
INFO = 'INFO'
INPUT = 'INPUT'


def main():
    """Main function to build iNethi server"""
    log = Log()
    device = {}
    log.log('---Welcome to the iNethi Builder v1.0.1---', SUCCESS)
    log.log(
        'Please ensure you have followed the instructions in the README.md '
        'file before running the iNethi builder.',
        WARNING
    )
    print()

    log.log('WOULD YOU LIKE TO USE SAVED LOGIN DETAILS?', INPUT)
    invalid_selection = True
    use_existing = ''
    while invalid_selection:
        use_existing = input(
            'Use existing login details? [y/n] '
        ).strip().lower()
        if use_existing == 'y' or use_existing == 'n':
            use_existing = False if use_existing == 'n' else True
            invalid_selection = False
        else:
            log.log('Please enter \'y\' or \'n\'.', ERROR)
    if use_existing:
        device_data = load_device_logins_from_yaml(SAVED_DEVICES)
        if device_data:
            if device_data:
                devices = device_data['login_details']
                log.log('Found existing login details:', INFO)
                for i, device in enumerate(devices, 1):
                    print(
                        f"{i}) Name: {device['name']}, "
                        f"IP Address: {device['ip']}, "
                        f"Username: {device['user']}, "
                        f"auth_method: {device['auth_method']} "
                        f"auth_value: {device['auth_value']}")
                log.log('CHOOSE A DEVICE TO USE', INPUT)
                invalid_selection = True
                while invalid_selection:
                    device_choice = int(
                        input(
                            "Enter the number of the device you want to use: "
                        )
                    )
                    if device_choice > len(devices) or device_choice < 1:
                        log.log('ERROR: Please enter a valid number.', ERROR)
                    else:
                        device = devices[device_choice - 1]
                        invalid_selection = False

        else:
            log.log(f'ERROR: devices not found in{SAVED_DEVICES}', ERROR)
            exit(1)
    else:
        log.log('ENTER YOUR REMOTE SERVER IP ADDRESS', INPUT)
        ip = input('IP Address: ').strip().lower()
        log.log('ENTER THE REMOTE SERVER USERNAME', INPUT)
        username = input('Username: ').strip().lower()
        log.log('CHOOSE YOU AUTHENTICATION METHOD', INPUT)
        print('1. Password')
        print('2. Key')
        invalid_selection = True
        auth_method = ''
        while invalid_selection:
            auth_method = input('Choice [1,2]: ').strip().lower()
            if auth_method == '1' or auth_method == '2':
                invalid_selection = False
            else:
                log.log('ERROR: Please enter a valid choice.', ERROR)

        auth_value = ''
        if auth_method == '1':
            log.log('ENTER YOUR REMOTE SERVER\'S PASSWORD', INPUT)
            auth_value = input('Password: ')
        elif auth_method == '2':
            log.log(
                'ENTER THE ABSOLUTE PATH TO YOUR REMOTE SERVER\'S KEY',
                INPUT
            )
            auth_value = input('Key path: ')
        log.log('You have entered the following details:', INFO)
        print('IP Address: ', ip)
        print('Username: ', username)
        auth_method = 'password' if auth_method == '1' else 'key'
        print('Auth method: ', auth_method)
        print('Auth value: ', auth_value)
        print()
        device = {
            'auth_method': auth_method,
            'auth_value': auth_value,
            'ip': ip,
            'user': username
        }
        invalid_selection = True
        save = ''
        log.log('YOU CAN SAVE THESE DETAILS TO USE THEM AGAIN LATER', INPUT)
        while invalid_selection:
            save = input(
                'Would you like to save these details? [y/n]: '
            ).strip().lower()
            if save == 'y' or save == 'n':
                invalid_selection = False
            else:
                log.log('Please enter a valid choice.', ERROR)
        if save.lower() == 'y':
            log.log(
                'ENTER A UNIQUE NAME TO IDENTIFY THIS DEVICE IN THE FUTURE',
                INPUT
            )
            device_name = input('Device name: ')
            save_device_login_to_yaml(
                SAVED_DEVICES, device_name, ip,
                username, auth_method, auth_value
            )
    # save details to inventory
    write_to_inventory(
        device['ip'],
        device['user'],
        device['auth_method'],
        device['auth_value'],
        INVENTORY_PATH
    )

    log.log('SYSTEM SET UP', INPUT)
    skip_setup = False
    invalid_selection = True
    while invalid_selection:
        skip_setup = input(
            "Have you run the builder successfully before "
            "and want to skip system setup? [y/n] "
        ).strip().lower()
        if skip_setup == 'y' or skip_setup == 'n':
            invalid_selection = False
        else:
            log.log('ERROR: Please enter a valid choice.', ERROR)

    skip_setup = False if skip_setup == 'n' else True

    if not skip_setup:
        log.log(
            'Checking connection to server and system requirements...',
            INFO
        )
        system_check_result = run_playbook(SYSTEM_CHECKS, INVENTORY_PATH)
        if system_check_result != 0:
            log.log(
                'ERROR: System checks failed. This could be '
                'caused by a loss of connection '
                'with the remote server or an incompatible operating '
                'system. Ensure your server '
                'is running Ubuntu server',
                ERROR
            )
            exit(1)
        log.log(
            'Installing Docker...',
            INFO
        )
        system_setup_result = run_playbook(SYSTEM_SETUP, INVENTORY_PATH)
        if system_setup_result != 0:
            log.log('ERROR: System set up failed', ERROR)
            exit(1)
        log.log(
            'Setting up Grafana, Prometheus and Traefik...',
            INFO
        )
        traefik_result = run_playbook(TRAEFIK, INVENTORY_PATH)
        if traefik_result != 0:
            log.log('ERROR: Traefik set up failed', ERROR)
            exit(1)
        else:
            log.log(
                'You can now access Grafana at grafana.inethilocal.net, '
                'prometheus at prometheus.inethilocal.net and traefik at '
                'traefik.inethilocal.net',
                SUCCESS
            )

    print("Select services to install:")
    for idx, choice in enumerate(SERVER_CHOICES, 1):
        print(f"{idx}. {choice}")

    while True:
        try:
            selected_indexes = (
                input("Enter the numbers of the services you "
                      "want to install (comma-separated): ")
                .split(','))
            selected_services = \
                [SERVER_CHOICES[int(idx) - 1]
                 for idx in selected_indexes]
            break
        except IndexError:
            print("Error: One or more of the service "
                  "numbers you provided are out of "
                  "range. Please try again.")
        except ValueError:
            print(
                "Error: Invalid input detected. "
                "Please provide a comma-separated "
                "list of service numbers in base 10 "
                "format.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}. Please try again.")
    for service in selected_services:
        path = service_map[service]
        rc = run_playbook(path, INVENTORY_PATH)
        if rc != 0:
            log.log(
                f'ERROR: RUNNING {path}. '
                f'Please check the error message and try again.',
                ERROR
            )
            break


if '__main__' == __name__:
    main()
