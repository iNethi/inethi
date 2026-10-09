#!/usr/bin/env python3

import configparser

from libs.accounting_updates import AccountingUpdates

if __name__ == "__main__":

    config      = configparser.ConfigParser()
    config.read(['/etc/captive-portal/captive_portal.conf'])
    
    update_interval_min  = config.get('acct_updates', 'update_interval_min', fallback=2) 
    check_interval_sec  = config.get('acct_updates', 'check_interval_sec', fallback=30)
    state_file = config.get('acct_updates', 'state_file', fallback="/var/lib/captive-portal/portal_state.json")

    updates = AccountingUpdates(
        update_interval_min = int(update_interval_min),
        check_interval_sec = int(check_interval_sec),
        state_file = state_file
    )
    updates.start_monitor()

