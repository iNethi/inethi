import ansible_runner
from utils.log import Log

# define constants for logging
WARNING = 'WARNING'
SUCCESS = 'SUCCESS'
ERROR = 'ERROR'
HEADING = 'HEADING'
INFO = 'INFO'
INPUT = 'INPUT'
TASK_NAME = 'TASK_NAME'
TASK_ACTION_SUCCESS = 'TASK_ACTION_SUCCESS'
TASK_ACTION_INFO = 'TASK_ACTION_INFO'
TASK_ACTION_ERROR = 'TASK_ACTION_ERROR'


TASK_WIDTH = 50

log = Log()


def status_handler(data, runner_config):
    """Handles ansible runner status data with user-friendly messages."""

    status = data.get('status')
  
    status_messages = {
        'starting': '▶  Starting Ansible execution...',
        'running': '▶  Ansible is running...',
        'failed': '✗  Ansible execution failed',
        'successful': 'Ansible execution completed successfully!',
        'timeout': '⋯  Ansible execution timed out',
        'canceled': '—  Ansible execution was canceled'
    }

    user_message = status_messages.get(status, f"Status: {status}")

    if status in ['starting', 'running', 'successful']:
        log.log(user_message, SUCCESS)
    elif status in ['failed', 'timeout', 'canceled']:
        log.log(user_message, ERROR)
    else:
        log.log(user_message, INFO)


class AnsibleEventHandler:
    """Produces concise, hierarchical Ansible event messages."""

    IGNORE_EVENTS = {
        'verbose',
        'runner_on_start',
        'playbook_on_task_end',
    }

    QUIET_ACTIONS = {
        'debug',
        'set_fact',
        'include_tasks',
        'include_role',
        'import_tasks',
        'import_role',
        'gather_facts'
    }

    def __init__(self, log):
        self.log = log
        self.current_play = None
        self.current_task = None
        self.current_action = None

    def __call__(self, data):
        """Allow the instance to be used directly as Ansible's event_handler."""

        self.handle(data)

    def handle(self, data):
        event_type = data.get('event', 'unknown_event')
        #print(event_type);
        event_data = data.get('event_data', {}) or {}

        if event_type in self.IGNORE_EVENTS:
            return

        # ---------------------------------------------------------
        # Playbook started
        # ---------------------------------------------------------

        if event_type == 'playbook_on_start':
            self.current_play = None
            self.current_task = None
            self.current_action = None

            self.log.log(
                "\n── Playbook started ─────────────────────────\n",
                HEADING
            )
            return

        # ---------------------------------------------------------
        # Play started
        # ---------------------------------------------------------

        if event_type == 'playbook_on_play_start':
            play_name = (
                event_data.get('name')
                or event_data.get('play')
                or 'Unnamed play'
            )

            self.current_play = play_name
            self.current_task = None
            self.current_action = None

            self.log.log(
                f"{play_name}",
                HEADING
            )
            return

        # ---------------------------------------------------------
        # Task started
        # ---------------------------------------------------------

        if event_type == 'playbook_on_task_start':
            task_name = event_data.get('name', 'Unnamed task')
            task_action = event_data.get('task_action', '')
            
            #print(task_name)
            #print(task_action)

            self.current_task = task_name
            self.current_action = task_action

            if task_action in self.QUIET_ACTIONS:
                return

            self.log.log(
                f"        {task_name:<{TASK_WIDTH}}",
                TASK_NAME
            )
            return

        # ---------------------------------------------------------
        # Task OK
        # ---------------------------------------------------------

        if event_type == 'runner_on_ok':
            task_action = event_data.get(
                'task_action',
                self.current_action
            )

            if task_action in self.QUIET_ACTIONS:
                return

            result = event_data.get('res', {}) or {}

            if result.get('changed', False):
                message = "● Changed"
            else:
                message = "● OK"

            self.log.log(message, TASK_ACTION_SUCCESS)
            return

        # ---------------------------------------------------------
        # Task skipped
        # ---------------------------------------------------------

        if event_type == 'runner_on_skipped':
            self.log.log(
                "● Skipped",
                TASK_ACTION_INFO
            )
            return

        # ---------------------------------------------------------
        # Task failed
        # ---------------------------------------------------------

        if event_type == 'runner_on_failed':
            task_name = event_data.get(
                'name',
                self.current_task
            )

            result = event_data.get('res', {}) or {}

            self.log.log(
                f"● FAILED: {task_name}",
                TASK_ACTION_ERROR
            )

            error = result.get('msg')

            if error:
                self.log.log(
                    f"● {error}",
                    TASK_ACTION_ERROR
                )
            elif result.get('stderr'):
                self.log.log(
                    f"● {result['stderr'].strip()}",
                    TASK_ACTION_ERROR
                )

            return

        # ---------------------------------------------------------
        # Host unreachable
        # ---------------------------------------------------------

        if event_type == 'runner_on_unreachable':
            task_name = event_data.get(
                'name',
                self.current_task
            )

            result = event_data.get('res', {}) or {}

            message = result.get(
                'msg',
                'Host unreachable'
            )

            self.log.log(
                f"● UNREACHABLE: {task_name}",
                TASK_ACTION_ERROR
            )

            self.log.log(
                f"● {message}",
                TASK_ACTION_ERROR
            )

            return

        # ---------------------------------------------------------
        # Playbook summary
        # ---------------------------------------------------------

        if event_type == 'playbook_on_stats':
            stats = event_data.get('stats', {}) or {}

            self.log.log(
                "\n── Playbook completed ───────────────────────\n",
                HEADING
            )

            for host, host_stats in stats.items():

                ok_count = host_stats.get('ok', 0)
                changed_count = host_stats.get('changed', 0)
                failed_count = host_stats.get('failed', 0)
                skipped_count = host_stats.get('skipped', 0)
                unreachable_count = host_stats.get(
                    'unreachable',
                    0
                )

                if failed_count or unreachable_count:
                    level = ERROR
                elif changed_count:
                    level = SUCCESS
                else:
                    level = INFO

                self.log.log(
                    f"   {host}: "
                    f"{ok_count} ok, "
                    f"{changed_count} changed, "
                    f"{failed_count} failed, "
                    f"{unreachable_count} unreachable, "
                    f"{skipped_count} skipped",
                    level
                )

            return


def run_playbook(playbook_path, inventory_path, verbose=False):
    """Runs playbook using Ansible Runner and custom handlers."""

    # One handler instance for this execution.
    # It maintains current_play/current_task state.
    event_handler = AnsibleEventHandler(log)

    r = ansible_runner.run(
        private_data_dir="./",
        playbook=playbook_path,
        inventory=inventory_path,
        status_handler=status_handler,
        quiet=not verbose,
        event_handler=event_handler,
        envvars={
            'ANSIBLE_VAULT_PASSWORD_FILE': '.vault_password'
        }
    )

    return r.rc