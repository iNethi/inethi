import sys
import ansible_runner
import pathlib
import yaml
import os
from dotenv import load_dotenv


def my_status_handler(data, runner_config):
    print('Status...')
    print(data['status'])


def my_event_handler(data):
    if data.get('event_data'):
        event_data = data['event_data']
        if event_data.get('name'):
            print(event_data['name'])


def write_to_inventory(ip, user, password, inventory_path):
    with open(inventory_path, 'w') as f:
        f.write(f"[localserver]\n")
        f.write(f"{ip} ansible_user='{user}' ansible_password='{password}' "
                f"ansible_ssh_common_args='-o StrictHostKeyChecking=no' ansible_become_pass='{password}'\n")


def save_ip_to_config(ip, config_path):
    with open(config_path, 'w') as f:
        yaml.dump({'ip_address': ip}, f)


def run_playbook(playbook_name, playbook_dir_path, inventory_path):
    playbook_path = f"{playbook_dir_path}/{playbook_name}.yml"
    r = ansible_runner.run(private_data_dir="./", playbook=playbook_path, inventory=inventory_path,
                           status_handler=my_status_handler, quiet=False, event_handler=my_event_handler)

    # Check if playbook run was successful
    if r.rc != 0:
        print(f"Error running playbook: {playbook_name}")
        sys.exit(1)


def main():
    # Load .env file
    load_dotenv()
    ip = os.getenv("ip")
    user = os.getenv("user")
    password = os.getenv("password")
    print(f"You are using IP address {ip}, Username {user} and Password {password} to connect to the target server.")

    abs_path = pathlib.Path(__file__).parent.resolve()
    test_playbook_name = 'wordpress'
    test_server = "test_server_connection"
    playbook_dir_path = f"{abs_path}/playbooks"
    inventory_path = f"{abs_path}/playbooks/inventory"
    config_path = f"{abs_path}/playbooks/config.yml"

    # Write to variables to file
    write_to_inventory(ip, user, password, inventory_path)
    save_ip_to_config(ip, config_path)

    # Run initial playbooks
    run_playbook(test_server, playbook_dir_path, inventory_path)

    run_playbook(test_playbook_name, playbook_dir_path, inventory_path)


if __name__ == '__main__':
    main()
