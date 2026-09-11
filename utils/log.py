"""
Enhanced logging utility for the iNethi builder
Uses beautiful colors and icons for better user experience
"""
from utils.colors import (
    heading, input_prompt, task_name, task_action_info, task_action_error, task_action_success,
    print_success, print_error, print_warning, print_info
)


class Log:
    def __init__(self):
        # Legacy constants for backward compatibility
        self.warning = 'WARNING'
        self.success = 'SUCCESS'
        self.error = 'ERROR'
        self.heading = 'HEADING'
        self.info = 'INFO'
        self.input = 'INPUT'
        self.task_name = 'TASK_NAME'
        self.task_action_error = 'TASK_ACTION_ERROR'
        self.task_action_info = 'TASK_ACTION_INFO'
        self.task_action_success = 'TASK_ACTION_SUCCESS'

    def log(self, message, level):
        """Log a message with enhanced colors and icons"""
        if level == self.warning:
            print_warning(message)
        elif level == self.success:
            print_success(message)
        elif level == self.error:
            print_error(message)
        elif level == self.heading:
            print(heading(f"    {message}    "))
        elif level == self.info:
            print_info(message)
        elif level == self.input:
            print(input_prompt(message))
        elif level == self.task_name:
            print(task_name(message), end='', flush=True)
        elif level == self.task_action_success:
            print(task_action_success(message))
        elif level == self.task_action_info:
            print(task_action_info(message))
        elif level == self.task_action_error:
            print(task_action_error(message))
        else:
            print(message)
