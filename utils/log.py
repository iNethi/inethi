"""
Enhanced logging utility for the iNethi builder
Uses beautiful colors and icons for better user experience
"""
from utils.colors import (
    heading, input_prompt,
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

    def log(self, message, level):
        """Log a message with enhanced colors and icons"""
        if level == self.warning:
            print_warning(message)
        elif level == self.success:
            print_success(message)
        elif level == self.error:
            print_error(message)
        elif level == self.heading:
            print(heading(f"--- {message} ---"))
        elif level == self.info:
            print_info(message)
        elif level == self.input:
            print(input_prompt(message))
        else:
            print(message)
