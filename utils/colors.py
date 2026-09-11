"""
Color utilities for iNethi platform scripts
Provides consistent, beautiful colors for better user experience
"""

# ANSI color codes


class Colors:
    # Primary colors
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    GREY = '\033[90m'

    # Bright colors
    BRIGHT_BLUE = '\033[94;1m'
    BRIGHT_GREEN = '\033[92;1m'
    BRIGHT_YELLOW = '\033[93;1m'
    BRIGHT_RED = '\033[91;1m'
    BRIGHT_PURPLE = '\033[95;1m'
    BRIGHT_CYAN = '\033[96;1m'
    BRIGHT_GREY = '\033[90;1m'

    # Background colors
    BG_BLUE = '\033[44m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_RED = '\033[41m'
    BG_PURPLE = '\033[45m'
    BG_CYAN = '\033[46m'

    # Text formatting
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    ITALIC = '\033[3m'

    # Reset
    RESET = '\033[0m'
    CLEAR = '\033[2J'
    CLEAR_LINE = '\033[K'


# Color functions for different message types


def success(text: str) -> str:
    """Format success messages in green"""
    return f"{Colors.BRIGHT_GREEN}✓ {text}{Colors.RESET}"


def error(text: str) -> str:
    """Format error messages in red"""
    return f"{Colors.BRIGHT_RED}✗ {text}{Colors.RESET}"


def warning(text: str) -> str:
    """Format warning messages in yellow"""
    return f"{Colors.BRIGHT_YELLOW}⚠ {text}{Colors.RESET}"


def info(text: str) -> str:
    """Format info messages in blue"""
    return f"{Colors.GREY}ℹ {text}{Colors.RESET}"


def heading(text: str) -> str:
    """Format headings in bold cyan"""
    return f"{Colors.BRIGHT_GREY}{Colors.BOLD}{text}{Colors.RESET}"


def subheading(text: str) -> str:
    """Format subheadings in bold purple"""
    return f"{Colors.BRIGHT_PURPLE}{Colors.BOLD}{text}{Colors.RESET}"


def input_prompt(text: str) -> str:
    """Format input prompts in cyan"""
    return f"{Colors.CYAN}{text}{Colors.RESET}"


def highlight(text: str) -> str:
    """Highlight important text in bold yellow"""
    return f"{Colors.BRIGHT_YELLOW}{Colors.BOLD}{text}{Colors.RESET}"


def code(text: str) -> str:
    """Format code snippets in purple"""
    return f"{Colors.PURPLE}{text}{Colors.RESET}"


def url(text: str) -> str:
    """Format URLs in blue with underline"""
    return f"{Colors.BLUE}{Colors.UNDERLINE}{text}{Colors.RESET}"


def progress(text: str) -> str:
    """Format progress messages in green"""
    return f"{Colors.GREEN}→ {text}{Colors.RESET}"


def step(text: str) -> str:
    """Format step numbers in bold blue"""
    return f"{Colors.BRIGHT_BLUE}{Colors.BOLD}Step: {text}{Colors.RESET}"


def separator(char: str = "=", length: int = 60) -> str:
    """Create a colored separator line"""
    return f"{Colors.CYAN}{char * length}{Colors.RESET}"


def box(text: str, title: str = "") -> str:
    """Create a box around text"""
    lines = text.split('\n')
    max_length = max(len(line) for line in lines)

    if title:
        title_line = f" {title} "
        max_length = max(max_length, len(title_line))

    box_text = f"{Colors.CYAN}┌{'─' * (max_length + 2)}┐{Colors.RESET}\n"

    if title:
        padding = max_length - len(title_line)
        box_text += (f"{Colors.CYAN}│{Colors.RESET}{Colors.BRIGHT_CYAN}"
                     f"{title_line}{Colors.RESET}{' ' * padding}{Colors.CYAN}│{Colors.RESET}\n")
        box_text += f"{Colors.CYAN}├{'─' * (max_length + 2)}┤{Colors.RESET}\n"

    for line in lines:
        padding = max_length - len(line)
        box_text += f"{Colors.CYAN}│{Colors.RESET} {line}{' ' * padding} {Colors.CYAN}│{Colors.RESET}\n"

    box_text += f"{Colors.CYAN}└{'─' * (max_length + 2)}┘{Colors.RESET}"
    return box_text


def task_name(text: str) -> str:
    return f"{Colors.GREY}{text}{Colors.RESET}"


def task_action_success(text: str) -> str:
    return f"{Colors.GREEN}{text}{Colors.RESET}"


def task_action_info(text: str) -> str:
    return f"{Colors.GREY}{text}{Colors.RESET}"


def task_action_error(text: str) -> str:
    return f"{Colors.RED}{text}{Colors.RESET}"


def print_header(title: str, subtitle: str = ""):
    """Print a beautiful header"""
    print(separator())
    print(heading(f"  {title}"))
    if subtitle:
        print(info(f"  {subtitle}"))
    print(separator())
    print()


def print_section(title: str):
    """Print a section header"""
    print()
    print(subheading(f"  {title}"))
    print(separator("-", 40))


def print_step(step_num: int, description: str):
    """Print a numbered step"""
    print(step(f"{step_num}. {description}"))


def print_success(message: str):
    """Print a success message"""
    print(success(message))


def print_error(message: str):
    """Print an error message"""
    print(error(message))


def print_warning(message: str):
    """Print a warning message"""
    print(warning(message))


def print_info(message: str):
    """Print an info message"""
    print(info(message))


def print_progress(message: str):
    """Print a progress message"""
    print(progress(message))
