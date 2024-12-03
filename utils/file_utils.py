"""Utility methods to assist file operations when running the iNethi builder"""
import os

import yaml


def write_to_inventory(ip, user, auth_type, auth_value, inventory_path):
    try:
        with open(inventory_path, 'w') as f:
            f.write("[localserver]\n")
            if auth_type == 'password':
                f.write(
                    f"{ip} ansible_user='{user}' "
                    f"ansible_password='{auth_value}' "
                    f"ansible_ssh_common_args='-o StrictHostKeyChecking=no' "
                    f"ansible_become_pass='{auth_value}'\n"
                )
            elif auth_type == 'key':
                f.write(
                    f"{ip} ansible_user='{user}' "
                    f"ansible_ssh_private_key_file='{auth_value}' "
                    f"ansible_ssh_common_args='-o StrictHostKeyChecking=no'\n"
                )
        print(f"Inventory written successfully to {inventory_path}")
    except Exception as e:
        print(f"Failed to write to inventory: {e}")


def save_device_login_to_yaml(
        yaml_file_path, name, ip, user, auth_method, auth_value
):
    """Save device login to yaml file"""
    new_entry = {
        'name': name,
        'ip': ip,
        'user': user,
        'auth_method': auth_method,
        'auth_value': auth_value,
    }
    # Check if the YAML file exists
    if os.path.exists(yaml_file_path):
        # If the file exists, load the existing data
        with open(yaml_file_path, 'r') as file:
            data = yaml.safe_load(file)
        # Add the new entry to the list of checks
        data['login_details'].append(new_entry)
    else:
        # If the file does not exist, create a new data structure
        data = {'login_details': [new_entry]}

    # Save the data to the YAML file
    with open(yaml_file_path, 'w') as file:
        yaml.safe_dump(data, file)


def load_device_logins_from_yaml(yaml_file_path):
    """Load device logins from yaml file"""
    # Check if the YAML file exists
    if os.path.exists(yaml_file_path):
        # If the file exists, load the existing data
        with open(yaml_file_path, 'r') as file:
            data = yaml.safe_load(file)
            return data
    else:
        # If the file does not exist, create a new data structure
        return None
