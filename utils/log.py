"""Class that uses ANSI codes to print coloured output"""


class Log:
    def __init__(self):

        self.RED = '\033[31m'
        self.GREEN = '\033[32m'
        self.YELLOW = '\033[33m'
        self.BLUE = '\033[34m'
        self.BLUE_BACK = '\033[46m'
        self.END_COLOR = '\033[0m'
        self.UNDERLINE = '\033[4m'
        self.warning = 'WARNING'
        self.success = 'SUCCESS'
        self.error = 'ERROR'
        self.heading = 'HEADING'
        self.info = 'INFO'
        self.input = 'INPUT'

    def log(self, message, level):
        """Log a message"""
        if level == self.warning:
            print(self.YELLOW + message + self.END_COLOR)
        elif level == self.success:
            print(self.GREEN + message + self.END_COLOR)
        elif level == self.error:
            print(self.RED + message + self.END_COLOR)
        elif level == self.heading:
            print(self.BLUE_BACK + message + self.END_COLOR)
        elif level == self.info:
            print(self.BLUE + message + self.END_COLOR)
        elif level == self.input:
            print(self.UNDERLINE + message + self.END_COLOR)
        else:
            print(message)
