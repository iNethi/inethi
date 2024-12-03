import ansible_runner
from utils.log import Log

# define constants for logging
WARNING = 'WARNING'
SUCCESS = 'SUCCESS'
ERROR = 'ERROR'
HEADING = 'HEADING'
INFO = 'INFO'
INPUT = 'INPUT'
log = Log()


def status_handler(data, runner_config):
    """Handles ansible runner status data."""
    status = data.get('status')
    if status == 'starting' or status == 'running':
        log.log(f'STATUS: {status}', SUCCESS)
    elif status == 'failed':
        log.log(f'STATUS: {status}', ERROR)
        print(data)


def event_handler(data):
    """Handles ansible runner event data."""
    # Log the event for debugging purposes
    event_type = data.get('event', 'unknown_event')

    # skip for conciseness
    if event_type == 'verbose':
        return
    log.log(f"EVENT: {event_type}", INFO)

    # Initialize output string
    output_str = ''

    # Check for task and name fields
    task = data.get('event_data', {}).get('task')
    name = data.get('event_data', {}).get('name')
    if task:
        output_str += f"TASK: {task}"
    if name:
        if task:
            output_str += f", NAME: {name}"
        else:
            output_str += f"NAME: {name}"

    # Check for failed tasks
    if 'fatal' in data.get('stdout'):
        log.log(f"ERROR: Task {task or 'unknown task'} failed.", ERROR)
        err_out = data.get('event_data', {}).get('res', {}).get('stderr_lines')
        if err_out:
            log.log("DETAILS", ERROR)
            log.log(f"{err_out}", ERROR)
        return

    # Log successful tasks or unprocessed events
    if output_str:
        log.log(output_str, SUCCESS)
    elif ('PLAY RECAP' in data.get('stdout')
          or 'playbook_on_start' in data.get('event')):
        log.log(f"{data.get('stdout')}", INFO)
        return
    else:
        log.log(f"Unprocessed event data: {data}", WARNING)


def run_playbook(playbook_path, inventory_path):
    """Runs playbook using ansible and custom handlers."""
    r = ansible_runner.run(
        private_data_dir="./",
        playbook=playbook_path,
        inventory=inventory_path,
        status_handler=status_handler,
        quiet=True,
        event_handler=event_handler,
    )
    return r.rc
