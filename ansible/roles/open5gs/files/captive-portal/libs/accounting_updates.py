# accounting_updates.py
import logging
import json
import time
from datetime import datetime
import configparser

from libs.captive_portal_accounting import (
    CaptivePortalAccounting,  
    RADIUSAccountingHandler
)

from libs.traffic_accounting import TrafficAccounting

class AccountingUpdates:
    """Update data usage info on active sessions"""
    
    def __init__(self, 
        update_interval_min : int = 2,
        check_interval_sec  : int = 30,
        state_file          : str = "/var/lib/captive-portal/portal_state.json"        
    ):
        """
        Initialize Accounting Updates Class
        
        Args:
            update_interval_min : The interval each device with active session's udage will be updated to the back-end
            check_ineterval_sec : How often to check for changes in the list of active devices
            state_file          : The file that shows a list of devices that is was detected
        """        
        self.update_interval_min    = update_interval_min
        self.check_interval_sec     = check_interval_sec
        self.state_file             = state_file
        
        self.update_interval_sec    = self.update_interval_min * 60 #Minutes to seconds
        self.logger                 = self._setup_logging()     
        self.logger.info("Starting Up Accounting Updates")
        
        # Track when we last triggered an action for each session
        self.last_triggered         = {}  # session_id -> last trigger timestamp
        
        config      = configparser.ConfigParser()
        config.read(['/etc/captive-portal/captive_portal.conf'])
        
        radius_server   = config.get('radius_server', 'radius_server', fallback='192.168.1.1') 
        radius_secret   = config.get('radius_server', 'radius_secret', fallback='AP-007')
        acct_port       = config.get('radius_server', 'radius_acct_port', fallback=1813)
        timeout         = config.get('nas_info', '1.0', fallback=5)
        
        self.radius_acct = RADIUSAccountingHandler(
            radius_server   = radius_server,
            radius_secret   = radius_secret,
            radius_port     = int(acct_port),
            timeout         = int(timeout)
        )

        # Create accounting service
        self.accounting = CaptivePortalAccounting(
            name="RADIUSdesk Captive Portal Accounting",
            handler=self.radius_acct
        )
        
        nas_ip_address  = config.get('nas_info', 'nas_ip_address', fallback='192.168.1.1') 
        nas_identifier  = config.get('nas_info', 'nas_identifier', fallback='AP-007')
        nas_port_type   = config.get('nas_info', 'nas_port_type', fallback='Wireless-802.11')
        rd_captive_portal_version   = config.get('nas_info', '1.0', fallback='5.0')
        
        self.nas_info = {
            "nas_ip_address": nas_ip_address,
            "nas_identifier": nas_identifier,
            "nas_port_type" : nas_port_type,
            "rd_captive_portal_version": rd_captive_portal_version
        }
        
        self.subnet  = "172.16.0.0/16"
        self.traffic = TrafficAccounting(subnet=self.subnet)      
           
    def start_monitor(self):
        try:
            while True:
                self._check_sessions()
                self.logger.info(f"Waiting {self.check_interval_sec} seconds until next check...")
                time.sleep(self.check_interval_sec)
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")
    
    def _load_sessions(self):
        """Load current sessions from JSON file"""
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                return data.get('devices', {})
        except FileNotFoundError:
            self.logger.error(f"File {self.state_file} not found yet...")
            return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing self.state_file: {e}")
            return {}
            
    def _perform_action(self, username, session_id, session_start, elapsed_minutes, trigger_count,ip):
        """Do something every 10 minutes"""
        print(f"\n{'='*60}")
        print(f"ACTION TRIGGERED - #{trigger_count}")
        print(f"  Username: {username}")
        print(f"  Session ID: {session_id}")
        print(f"  Session started: {session_start}")
        print(f"  Active for: {elapsed_minutes:.1f} minutes")
        print(f"  Next action in: {self.update_interval_min} minutes")
        print(f"{'='*60}\n")
        
        # ============================================
        # ADD YOUR CUSTOM ACTION HERE
        # ============================================
        
        self.logger.info(f"#{trigger_count} - User {username} active for {elapsed_minutes:.1f} minutes")    
        usage = self.traffic.get_bytes(ip)
        start = datetime.fromisoformat(session_start)
        session_time = int((datetime.now()-start).total_seconds())
        additional_attrs = {
            'user_name'         : username,
            'acct_session_id'   : session_id,
            'framed_ip_address' : ip, 
            'acct_session_time' : session_time,
            'acct_input_octets' : usage['bytes_in'],
            'acct_output_octets': usage['bytes_out'],
        }
        print(additional_attrs)
        self.accounting.accounting_update(nas_info=self.nas_info,additional_attributes=additional_attrs)
    
            
    def _check_sessions(self):
        """Check all sessions and trigger actions every 10 minutes"""
        sessions = self._load_sessions()
      
        if not sessions:
            self.logger.info(f"No active sessions")
            return
        
        self.logger.info(f"Checking {len(sessions)} active session(s)...")
        
        now = datetime.now()
        current_session_ids = set()
        
        for ip, session_data in sessions.items():
            ip  = session_data.get('ip', '')
            username = session_data.get('username', 'unknown')
            session_id = session_data.get('session_id', '')
            session_start_str = session_data.get('session_start', '')
            
            if not session_id or not session_start_str:
                continue
            
            current_session_ids.add(session_id)
            
            # Parse the session start time
            try:
                session_start = datetime.fromisoformat(session_start_str)
            except ValueError:
                self.logger.info(f"Error parsing date for {username}")
                continue
            
            # Calculate how long the session has been active
            elapsed = (now - session_start).total_seconds()
            elapsed_minutes = elapsed / 60
            
            # Calculate which 10-minute block we're in (1-based)
            current_block = int(elapsed // self.update_interval_sec) + 1
            
            # Get last triggered block for this session
            last_block = self.last_triggered.get(session_id, 0)
            
            # If we've entered a new 10-minute block, trigger action
            if current_block > last_block and elapsed >= self.update_interval_sec:
                self.logger.info(f"-> {username}: {elapsed_minutes:.1f} minutes active - TRIGGERING #{current_block}")
                self._perform_action(username, session_id, session_start_str, elapsed_minutes, current_block,ip)
                self.last_triggered[session_id] = current_block
            else:
                if elapsed < self.update_interval_sec:
                    remaining = self.update_interval_sec - elapsed
                    remaining_minutes = remaining / 60
                    self.logger.info(f"-> {username}: active {elapsed_minutes:.1f} min, first trigger in {remaining_minutes:.1f} min")
                else:
                    # Calculate time until next trigger
                    next_trigger = ((last_block + 1) * self.update_interval_sec) - elapsed
                    next_minutes = next_trigger / 60
                    self.logger.info(f"-> {username}: active {elapsed_minutes:.1f} min, next trigger in {next_minutes:.1f} min (already triggered {last_block} time(s))")
        
        # Clean up sessions that are no longer active
        expired_sessions = set(self.last_triggered.keys()) - current_session_ids
        if expired_sessions:
            print(f"  Removing {len(expired_sessions)} expired session(s) from tracking")
            for session_id in expired_sessions:
                del self.last_triggered[session_id]
        
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/var/log/captive-portal/accounting_updates.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
