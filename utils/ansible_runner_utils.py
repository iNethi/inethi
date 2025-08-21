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
    """Handles ansible runner status data with user-friendly messages."""
    status = data.get('status')
    status_messages = {
        'starting': '🚀 Starting Ansible execution...',
        'running': '⚡ Ansible is running...',
        'failed': '❌ Ansible execution failed',
        'successful': '🎉 Ansible execution completed successfully!',
        'timeout': '⏰ Ansible execution timed out',
        'canceled': '🚫 Ansible execution was canceled'
    }

    user_message = status_messages.get(status, f"Status: {status}")
    if status in ['starting', 'running', 'successful']:
        log.log(user_message, SUCCESS)
    elif status in ['failed', 'timeout', 'canceled']:
        log.log(user_message, ERROR)
    else:
        log.log(user_message, INFO)


def event_handler(data):
    """Handles ansible runner event data with user-friendly messages."""
    event_type = data.get('event', 'unknown_event')

    # Skip verbose and noisy events
    skip_events = ['verbose', 'runner_on_start', 'playbook_on_task_start']
    if event_type in skip_events:
        return

    # User-friendly event mapping
    event_messages = {
        'playbook_on_start': '📋 Starting playbook execution...',
        'playbook_on_play_start': '🎭 Starting play...',
        'playbook_on_task_start': '⚡ Starting task...',
        'runner_on_start': '🔄 Running...',
        'runner_on_ok': '✅ Complete!',
        'runner_on_failed': '❌ Failed!',
        'runner_on_skipped': '⏭️  Skipped',
        'runner_on_unreachable': '🚫 Unreachable',
        'playbook_on_stats': '📊 Playbook completed',
        'playbook_on_play_end': '🎭 Play completed',
        'playbook_on_task_end': '⚡ Task completed'
    }

    # Get user-friendly message or use event type as fallback
    user_message = event_messages.get(event_type, f"Event: {event_type}")

    # Get task name for context
    task_name = data.get('event_data', {}).get('name', '')
    task_action = data.get('event_data', {}).get('task_action', '')

    # Build context string
    context = ''
    if task_name:
        context = f" - {task_name}"
    elif task_action:
        context = f" - {task_action}"

    # Handle special cases
    if event_type == 'runner_on_failed':
        log.log(f"❌ Task failed{context}", ERROR)
        # Show error details if available
        result = data.get('event_data', {}).get('res', {})
        if result and 'msg' in result:
            log.log(f"   Error: {result['msg']}", ERROR)
        return
    elif event_type == 'runner_on_ok':
        # Only show completion for tasks that actually do something
        task_action = data.get('event_data', {}).get('task_action', '')
        if task_action and task_action not in ['debug', 'set_fact']:
            log.log(f"✅ Task completed{context}", SUCCESS)
        return
    elif event_type == 'runner_on_skipped':
        log.log(f"⏭️  Task skipped{context}", INFO)
        return
    elif event_type == 'playbook_on_stats':
        # Show playbook summary
        stats = data.get('event_data', {}).get('stats', {})
        if stats:
            for host, host_stats in stats.items():
                ok_count = host_stats.get('ok', 0)
                changed_count = host_stats.get('changed', 0)
                failed_count = host_stats.get('failed', 0)
                skipped_count = host_stats.get('skipped', 0)
                log.log(
                    f"📊 {host}: {ok_count} ok, {changed_count} changed, "
                    f"{failed_count} failed, {skipped_count} skipped",
                    INFO)
        return
    elif 'PLAY RECAP' in data.get('stdout', ''):
        # Show play recap
        log.log("📊 Playbook Summary:", INFO)
        log.log(data.get('stdout', ''), INFO)
        return

    # Log the user-friendly message
    log.log(f"{user_message}{context}", INFO)


def run_playbook(playbook_path, inventory_path, verbose=False):
    """Runs playbook using ansible and custom handlers."""
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
