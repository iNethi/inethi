#!/usr/bin/env python3
# /usr/local/bin/captive_portal_controller.py

import subprocess
import time
import random
import logging
import os
import signal
import sys
import json
import threading
import ipaddress
import configparser
import re

from datetime import datetime
from enum import Enum
from ipaddress import ip_address, ip_network
from collections import defaultdict

from pathlib import Path

import json

from libs.captive_portal_authentication import (
    CaptivePortalAuthentication,  
    RADIUSAuthenticationHandler
)

from libs.captive_portal_accounting import (
    CaptivePortalAccounting,  
    RADIUSAccountingHandler
)

from libs.traffic_accounting import TrafficAccounting
from libs.traffic_shaping import TrafficShaping

#May 2026 Add Walled Garden Functionality
from libs.walled_garden_manager import WalledGardenManager

import secrets

class DeviceState:
    """Represents state for a single device"""
    def __init__(self, ip_address):
        self.ip = ip_address
        self.detected = False
        self.redirect_rules_active = False
        self.first_seen = None
        self.last_activity = None
        self.session_id = None
        self.session_start = None
        self.username = None
        self.bw_up = None
        self.bw_down = None
        self.data_cap = None
        self.time_cap = None
    
    def to_dict(self):
        return {
            'ip': self.ip,
            'detected': self.detected,
            'redirect_rules_active': self.redirect_rules_active,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'session_id' : self.session_id if self.session_id else None,
            'session_start' : self.session_start.isoformat() if self.session_start else None,
            'username' : self.username if self.username else None,
            'bw_up' : self.bw_up if self.bw_up else None,
            'bw_down' : self.bw_down if self.bw_down else None,
            'data_cap' : self.data_cap if self.data_cap else None,
            'time_cap' : self.time_cap if self.time_cap else None
        }
    
    @classmethod
    def from_dict(cls, data):
        device = cls(data['ip'])
        device.detected = data.get('detected', False)
        device.redirect_rules_active = data.get('redirect_rules_active', False)
        if data.get('first_seen'):
            device.first_seen = datetime.fromisoformat(data['first_seen'])
        if data.get('last_activity'):
            device.last_activity = datetime.fromisoformat(data['last_activity'])
        device.session_id = data.get('session_id', None)
        if data.get('session_start'):
            device.session_start = datetime.fromisoformat(data['session_start'])
        return device

class CaptivePortalController:
    def __init__(self):
           
        print("=" * 50)
        print("Captive Portal Initial Prep")
        print("=" * 50)  
        
        self.shutdown_event = threading.Event()
        # Store device states
        self.devices = {}  # IP -> DeviceState object
        self.lock = threading.Lock()  # Thread safety
        
        self.conntrack_process = None
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        config      = configparser.ConfigParser()
        config.read(['/etc/captive-portal/captive_portal.conf'])
        
        subnet      =  config.get('captive_portal', 'subnet',  fallback="172.16.0.0/16")
        gateway     =  config.get('captive_portal', 'gateway', fallback="172.16.0.0.1")
        redirect_ip =  config.get('captive_portal', 'redirect_ip', fallback="164.160.89.129")
        redirect_http_port = config.get('captive_portal', 'redirect_http_port', fallback=80)
        redirect_https_port = config.get('captive_portal', 'redirect_https_port', fallback=443)
        state_file = config.get('captive_portal', 'state_file', fallback="/var/lib/captive-portal/portal_state.json")
        overrides_file = config.get('captive_portal', 'overrides_file', fallback="/var/lib/captive-portal/device_overrides.json")
        device_timeout = config.get('captive_portal', 'device_timeout', fallback=3600)
        max_devices = config.get('captive_portal', 'max_devices', fallback=100)
        
        self.walled_garden_entries = None

        if config.has_option('walled_garden', 'entries_csv'):
            entries_str = config.get('walled_garden', 'entries_csv')
            entries = [e.strip() for e in entries_str.split(',')]
            self.walled_garden_entries = entries
        
        self.subnet = subnet
        self.subnet_obj = ip_network(subnet)
        self.gateway = gateway
        self.redirect_ip = redirect_ip
        self.redirect_http_port = int(redirect_http_port)
        self.redirect_https_port = int(redirect_https_port)
        self.state_file = state_file
        self.overrides_file = overrides_file
        self.device_timeout = int(device_timeout)
        self.max_devices = int(max_devices)
               
        self.logger = self.setup_logging()
        
        #Clear all the old states
        self.clean_start()
        
        #Add the walled garden
        self.add_walled_garden()
      
        # Load or create initial state
        self.load_state()
        
        radius_server   = config.get('radius_server', 'radius_server', fallback='192.168.1.1') 
        radius_secret   = config.get('radius_server', 'radius_secret', fallback='testing123')
        acct_port       = config.get('radius_server', 'radius_acct_port', fallback=1813)
        timeout         = config.get('nas_info', '1.0', fallback=5)
        
        #Do RADIUS Classes
        self.radius_auth = RADIUSAuthenticationHandler(
            radius_server = radius_server,
            radius_secret = radius_secret,
            timeout = int(timeout)
        )
        
        self.auth_service = CaptivePortalAuthentication(
            name="Flexible WiFi Auth",
            handler=self.radius_auth
        )
        
        self.radius_acct = RADIUSAccountingHandler(
            radius_server = radius_server,
            radius_secret = radius_secret,
            radius_port = int(acct_port),
            timeout = int(timeout)
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
            "nas_port_type": nas_port_type,
            "rd_captive_portal_version": rd_captive_portal_version 
        }
        
        # Additional attributes can be passed separately
        self.additional_attrs = {}
        
        self.traffic = TrafficAccounting(subnet=self.subnet)
        
        bw_iface   = config.get('traffic_shaping', 'bw_iface', fallback='br0') 
        ifb_iface  = config.get('traffic_shaping', 'ifb_iface', fallback='ifb0')
        bw_total   = config.get('traffic_shaping', 'bw_total', fallback='100mbit')
        
        self.shaping = TrafficShaping(
            bw_iface = bw_iface,
            ifb_iface = ifb_iface,
            bw_total = bw_total
        )       
    
    def signal_handler(self, signum, frame):
        """Clean shutdown on signals"""
        print(f"\nReceived signal {signum}, shutting down...")
        self.shutdown_event.set()
    
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/var/log/captive-portal/captive_portal.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    def clean_start(self):
        """Do a clean start of the Captive Portal"""
        try:
            flash_cmd = [
                'iptables', '-t', 'nat', '-F', 'PREROUTING',
            ]      
            subprocess.run(flash_cmd, stderr=subprocess.DEVNULL)
            self.logger.info(f"Flash PREROUTING nat iptables")         
        except Exception as e:
            self.logger.error(f"Error clearing redirect rules")
       
        try:        
            flash_conntr = [
                'conntrack', '-F'
            ]
            subprocess.run(flash_conntr, stderr=subprocess.DEVNULL)
            self.logger.info(f"Flash conntrack")
        except Exception as e:
            self.logger.error(f"Error clearing conntrack")
            
        try:        
            flash_forward = [
                'iptables', '-t', 'nat', '-F', 'FORWARD',
            ]
            subprocess.run(flash_conntr, stderr=subprocess.DEVNULL)
            self.logger.info(f"Flash forward table")
        except Exception as e:
            self.logger.error(f"Error clearing forward rules")
              
        try:
            if os.path.exists(self.state_file):
                os.remove(self.state_file)
                self.logger.info(f"Remove {self.state_file}")
        except Exception as e:
            self.logger.error(f"Error loading state: {e}")
        
    
    def load_state(self):
        """Load persistent state from file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    data = json.load(f)                   
                    # Load devices
                    devices_data = data.get('devices', {})
                    for ip, device_data in devices_data.items():
                        device = DeviceState.from_dict(device_data)
                        self.devices[ip] = device                      
                    self.logger.info(f"Loaded state: {len(self.devices)} devices")
            else:
                self.logger.info(f"No state file found create the first one")
                self.save_state()
        except Exception as e:
            self.logger.error(f"Error loading state: {e}")
    
    def save_state(self):
        """Save persistent state to file"""
        try:
            with self.lock:        
                devices_dict = {}
                for ip, device in self.devices.items():
                    devices_dict[ip] = device.to_dict()
                
                state = {
                    'devices': devices_dict,
                    'last_updated': datetime.now().isoformat(),
                    'subnet': self.subnet,
                    'device_count': len(self.devices)
                }
                with open(self.state_file, 'w') as f:
                    json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving state: {e}")
    
    def get_device_rules(self, device):
        """Get rules for this device e.g. if we have to redirect (Captive Portal) or not"""
        
        result = self.auth_service.authenticate(
            username=device.ip,
            password=device.ip,
            nas_info=self.nas_info,
            additional_attributes={'framed_ip_address' : device.ip}
        )
        
        self.logger.info(f"RADIUS SAYS - Can IP {device.ip} go through {result.get('success')}")
        
        device.username = None # Clear the username first
        
        if result.get('success'):
        
            attrs       = result.get("attributes", {})
            usernames   = attrs.get("user_name", [])
            username    = usernames[0] if usernames else None
            if username:
                device.username = username
            
            #Shaping WISPr-Bandwidth-Max-Up and WISPr-Bandwidth-Max-Down    
            bw_ups  = attrs.get("wispr_bandwidth_max_up", [])
            bw_up   = bw_ups[0] if bw_ups else None
            if bw_up:
                device.bw_up = f'{bw_up // 1024}kbit'  # Integer division to get kbit
            else:
                device.bw_up = None
                
            bw_downs  = attrs.get("wispr_bandwidth_max_down", [])
            bw_down   = bw_downs[0] if bw_downs else None
            if bw_down:
                device.bw_down = f'{bw_down // 1024}kbit'  # Integer division to get kbit
            else:
                device.bw_down = None
                
            #Data Cap
            data_limits = attrs.get("mikrotik_total_limit", [])
            data_limit  = data_limits[0] if data_limits else None
            if data_limit:
                #Check if there is gigawords involved
                gigawords = attrs.get("mikrotik_total_limit_gigawords", [])
                gigaword  = gigawords[0] if gigawords else None
                if gigaword:
                    data_limit = (int(gigaword) * 4294967296) + int(data_limit)
                      
                device.data_cap = int(data_limit)   
            
            #Time Cap
            time_limits = attrs.get("session_timeout", [])
            time_limit  = time_limits[0] if time_limits else None
            if time_limit:
                device.time_cap = int(time_limit)
                                                                                    
        print("Authentication Result:")
        print(json.dumps(result, indent=2))                              
        device.redirect_rules_active = not result.get('success');
        
    def add_walled_garden(self):
        """Add rules at the top of the list to"""
        try:      
            self.logger.info(f"Adding Walled Garden Hosts and Subnets")
            
            wg = WalledGardenManager(
                ipset_name="walled_garden_list",
                source_subnet=self.subnet
            )
            
            wg.cleanup()
                       
            if self.walled_garden_entries:
                wg.add_entries(self.walled_garden_entries)
                wg.create_ipset(force_recreate=True)
                wg.populate_ipset()
                wg.insert_iptables_rule(position=1)
                wg.insert_prerouting_bypass(position=1)
                wg.verify_rules()            
                # Optional: List entries
                wg.list_entries()
                             
        except Exception as e:
            self.logger.error(f"Error adding Walled Garden Rules: {e}")
            return False
   
    def get_walled_garden_rule_number(self):
        """get the rule number for walled garden set"""
        cmd = [
            "iptables",
            "-L", 'FORWARD',
            "--line-numbers",
            "-n"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        for line in result.stdout.splitlines():
            if "match-set walled_garden_list" in line:
                match = re.match(r"^\s*(\d+)", line)
                if match:
                    return int(match.group(1))

        return None 
   
    def add_block_rules(self, device_ip):
        """Block all traffic except port 53 UDP and TCP"""
        try:
        
            #If there is a walled garden then we need to insert AFTER the Walled Garden
            rule_num = self.get_walled_garden_rule_number()

            # If found -> insert AFTER it
            # If not found -> insert at TOP
            insert_position = rule_num + 1 if rule_num else 1             
        
            # Check if rule already exists
            check_cmd = [
                'iptables', '-C', 'FORWARD',
                '-s', device_ip, '-p', 'tcp', '-m', 'multiport', '!', '--dports', '53',
                '-j', 'DROP'
            ]
            result = subprocess.run(check_cmd, stderr=subprocess.DEVNULL)
            
            if result.returncode != 0:
                # Rule doesn't exist, add it
                cmd = [
                    'iptables', '-I', 'FORWARD',str(insert_position),
                    '-s', device_ip, '-p', 'tcp', '-m', 'multiport', '!', '--dports', '53',
                    '-j', 'DROP'
                ]
                subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
                self.logger.debug(f"DROPPING FORWARD TCP traffic from {device_ip}")
                cmd = [
                    'iptables', '-I', 'FORWARD',str(insert_position),
                    '-s', device_ip, '-p', 'udp', '-m', 'multiport', '!', '--dports', '53',
                    '-j', 'DROP'
                ]
                subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
                self.logger.debug(f"DROPPING FORWARD UDP traffic from {device_ip}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error blocking forward traffic from {device_ip}: {e}")
            return False
         
    def remove_block_rules(self, device_ip):
        """Remove iptables redirect rule"""
        try:
            cmd = [
                'iptables', '-D', 'FORWARD',
                '-s', device_ip, '-p', 'tcp', '-m', 'multiport', '!', '--dports', '53',
                '-j', 'DROP'
            ]
            subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
            self.logger.debug(f"Removed DROPPING FORWARD TCP for {device_ip}")
            
            cmd = [
                'iptables', '-D', 'FORWARD',
                '-s', device_ip, '-p', 'udp', '-m', 'multiport', '!', '--dports', '53',
                '-j', 'DROP'
            ]
            subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
            self.logger.debug(f"Removed DROPPING FORWARD UDP for {device_ip}")
            return True
        except subprocess.CalledProcessError:
            # Rule might not exist, that's fine
            return False
        except Exception as e:
            self.logger.error(f"Error removing redirect rule for {device_ip}:{port}: {e}")
            return False 
      
    def add_redirect_rule(self, device_ip, port, redirect_port):
        """Add iptables redirect rule for specific device and port"""
        try:
            # Check if rule already exists
            check_cmd = [
                'iptables', '-t', 'nat', '-C', 'PREROUTING',
                '-s', device_ip, '-p', 'tcp', '--dport', str(port),
                '-j', 'DNAT', '--to-destination', f"{self.redirect_ip}:{redirect_port}"
            ]
            result = subprocess.run(check_cmd, stderr=subprocess.DEVNULL)
            
            if result.returncode != 0:
                # Rule doesn't exist, add it
                cmd = [
                    'iptables', '-t', 'nat', '-A', 'PREROUTING',
                    '-s', device_ip, '-p', 'tcp', '--dport', str(port),
                    '-j', 'DNAT', '--to-destination', f"{self.redirect_ip}:{redirect_port}"
                ]
                subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
                self.logger.debug(f"Added rule for {device_ip}:{port} -> {self.redirect_ip}:{redirect_port}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error adding redirect rule for {device_ip}:{port}: {e}")
            return False
    
    def remove_redirect_rule(self, device_ip, port, redirect_port):
        """Remove iptables redirect rule"""
        try:
            cmd = [
                'iptables', '-t', 'nat', '-D', 'PREROUTING',
                '-s', device_ip, '-p', 'tcp', '--dport', str(port),
                '-j', 'DNAT', '--to-destination', f"{self.redirect_ip}:{redirect_port}"
            ]
            subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
            self.logger.debug(f"Removed rule for {device_ip}:{port}")
            return True
        except subprocess.CalledProcessError:
            # Rule might not exist, that's fine
            return False
        except Exception as e:
            self.logger.error(f"Error removing redirect rule for {device_ip}:{port}: {e}")
            return False
    
    def update_traffic_rules(self, device):
        """Update recording of traffic or not for this session"""    
        #Traffic recording or not
        with self.lock:
            if device.redirect_rules_active:
                usage = self.traffic.get_bytes(device.ip)
                if self.traffic.remove_ip(device.ip):
                    self.logger.info(f"Stopped tracking {device.ip}")
                    if device.session_id:
                        session_time = int((datetime.now()-device.session_start).total_seconds())
                        self.logger.info(f"Session on {device.ip} lasted {session_time} seconds")
                        self.stop_accounting(device,session_time,usage)
                        device.session_id       = None
                        device.session_start    = None
                        #device.username         = None #Don't remove it. If it is removed we can't do a mainal allow with accounting
                    
            else:
                if self.traffic.add_ip(device.ip):
                    self.logger.info(f"Started tracking {device.ip}")
                    device.session_id       = str(int(datetime.now().timestamp())) + str(self.get_unique_4_digits())
                    device.session_start    = datetime.now()
                    self.start_accounting(device)  

    def update_shaping(self, device):
        """Set shaping for device if specified """    
        #To Shape or not to shape
        with self.lock:
            if device.bw_up and device.bw_down:      
                if self.shaping.add_ip_with_speed(device.ip,device.bw_down,device.bw_up):
                    self.logger.info(f"Shaping {device.ip} to download {device.bw_down} and upload {device.bw_up}")

            else:
                if self.shaping.remove_ip(device.ip): 
                    self.logger.info(f"Shaping for {device.ip} cleared")           
    
        
    def get_unique_4_digits(self) -> str:
        random = secrets.randbelow(1000000)
        return f"{random:04d}"
        
    def start_accounting(self, device):
        additional_attrs = {
            'user_name'         : device.username,
            'acct_session_id'   : device.session_id,
            'framed_ip_address' : device.ip,  
            'acct_session_time' : 0 
        }
        self.accounting.accounting_start(nas_info=self.nas_info,additional_attributes=additional_attrs)
    
    def stop_active_session(self,device): 
         if device.session_id:
            usage = self.traffic.get_bytes(device.ip)
            self.traffic.reset_ip(device.ip)
            session_time = int((datetime.now()-device.session_start).total_seconds())
            self.logger.info(f"Session on {device.ip} lasted {session_time} seconds")
            self.stop_accounting(device,session_time,usage)
            device.session_id       = None
            device.session_start    = None
            
            self.save_state() 
    
    def stop_accounting(self,device,session_time,usage):
        additional_attrs = {
            'user_name'         : device.username,
            'acct_session_id'   : device.session_id,
            'framed_ip_address' : device.ip, 
            'acct_session_time' : session_time,
            'acct_input_octets' : usage['bytes_in'],
            'acct_output_octets': usage['bytes_out'],
        }
        print(additional_attrs)
        self.accounting.accounting_stop(nas_info=self.nas_info,additional_attributes=additional_attrs)
            
    def clear_conntrack(self, device):
        """Clear conntrack infor for device"""
        try:        
            src_conntr = [
                'conntrack', '-D', '--orig-src', device.ip
            ]
            subprocess.run(src_conntr, stderr=subprocess.DEVNULL)
            self.logger.info(f"Deleting conntrack for {device.ip}")
        except Exception as e:
            self.logger.error(f"Error deleting conntrack for {device.ip}")
            
        try:        
            dst_conntr = [
                'conntrack', '-D', '--orig-dst', device.ip
            ]
            subprocess.run(dst_conntr, stderr=subprocess.DEVNULL)
            self.logger.info(f"Deleting conntrack for {device.ip}")
        except Exception as e:
            self.logger.error(f"Error deleting conntrack for {device.ip}")
    
                
    def update_device_rules(self, device):
        """Update redirect rules for a specific device based on redirect_rules_active flag"""
        with self.lock:
            # Only apply rules if device has been detected
            if not device.detected:
                return
             
            if device.redirect_rules_active:
                self.logger.info(f"Redirect Rules Active is True: Activating redirection for {device.ip} to {self.redirect_ip}")
                self.add_redirect_rule(device.ip, 80, self.redirect_http_port)
                self.add_redirect_rule(device.ip, 443, self.redirect_https_port)
                self.add_block_rules(device.ip)              

            if not device.redirect_rules_active:
                self.logger.info(f"Redirect Rules Active is False: Removing redirection for {device.ip}")
                self.remove_redirect_rule(device.ip, 80, self.redirect_http_port)
                self.remove_redirect_rule(device.ip, 443, self.redirect_https_port)
                self.remove_block_rules(device.ip)
    
    def _remove_device(self, device):
        self.logger.info(f"***Removing {device.ip}***")
        self.remove_redirect_rule(device.ip, 80, self.redirect_http_port)
        self.remove_redirect_rule(device.ip, 443, self.redirect_https_port)
        self.remove_block_rules(device.ip)
        
        if device.session_id:
            usage = self.traffic.get_bytes(device.ip) # Get the usage before removing it          
            if self.traffic.remove_ip(device.ip):
                self.logger.info(f"Stopped tracking {device.ip}")
                session_time = int((datetime.now()-device.session_start).total_seconds())
                self.logger.info(f"Session on {device.ip} lasted {session_time} seconds")
                self.stop_accounting(device,session_time,usage)
                device.session_id       = None
                device.session_start    = None
                
        self.shaping.remove_ip(device.ip)
        
        return True 
    
    def check_data_time_caps(self):
        """Go through list of devices and test data and time caps if present"""
        now = datetime.now()
        
        for ip, device in self.devices.items():
            if device.session_start:
                #Time Cap
                if device.time_cap:  
                    if (now - device.session_start).total_seconds() > device.time_cap:
                        self.logger.info(f"Time Cap for {ip} reached - re-authenticating")
                        self._auth_sequence(device)
                        
                if device.data_cap:
                    usage = self.traffic.get_bytes(device.ip)
                    if usage['total'] > device.data_cap:
                        self.logger.info(f"Data Cap for {ip} reached - re-authenticating")
                        self._auth_sequence(device)       
    
    def cleanup_inactive_devices(self):
        """Remove rules for devices that haven't been active recently"""
        now = datetime.now()
        devices_to_remove = []
        modified = False
      
        for ip, device in self.devices.items():
            if device.detected and device.last_activity:
                a = (now - device.last_activity).total_seconds()
                if (now - device.last_activity).total_seconds() > self.device_timeout:
                    self.logger.info(f"Adding {ip} to devices that needs to be removed")
                    devices_to_remove.append(ip)
        
        for ip in devices_to_remove:
            if self._remove_device(self.devices[ip]):
                del self.devices[ip]
        
        if devices_to_remove:
            modified = True
            self.logger.info(f"Cleaned up {len(devices_to_remove)} inactive devices")
    
        if modified:
            # Now safe to save - lock is released
            self.save_state()    
    
    def is_ip_in_subnet(self, ip):
        """Check if IP belongs to our subnet"""
        try:
            return ip_address(ip) in self.subnet_obj
        except:
            return False
            
    def _auth_sequence(self,device):
    
        self.stop_active_session(device)
      
        self.get_device_rules(device)                  
        # Apply rules for this device
        self.update_device_rules(device)
        self.update_traffic_rules(device)
        self.update_shaping(device)      
        self.save_state()    
    
    def monitor_traffic(self):
        """Monitor for traffic from ANY device in the subnet"""    
        self.logger.info(f"Monitoring for traffic from any device in {self.subnet}......")
                      
        try:
            # Start conntrack process
            cmd = ['conntrack', '-E', '-o', 'extended']
            self.conntrack_process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True, 
                bufsize=1
            )
            
            # Make stdout non-blocking so we can check shutdown_event
            import fcntl
            fd = self.conntrack_process.stdout.fileno()
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            
            while not self.shutdown_event.is_set():
                try:
                    line = self.conntrack_process.stdout.readline()
                    if not line:
                        if self.conntrack_process.poll() is not None:
                            break
                        time.sleep(0.1)
                        continue
                    
                    line = line.strip()                    
                    if not line.startswith('[NEW]'):
                        continue
                                                                        
                    # Parse conntrack output to find source IP
                    # Example line: [NEW] tcp 6 120 SYN_SENT src=172.16.1.100 dst=8.8.8.8                 
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.startswith('src='):
                            src_ip = part.split('=')[1].split(':')[0]
                            
                            if src_ip in self.devices and self.devices[src_ip].detected:
                                # Already handled this device, just update activity if needed
                                self.devices[src_ip].last_activity = datetime.now()
                                continue  # Skip rule application, state saving, etc.
                            
                            # Check if this IP is in our subnet
                            if self.is_ip_in_subnet(src_ip):
                            
                                if src_ip == self.gateway:
                                    continue #Skip the gateway
                                
                                #Only NEW connections will end here since we skip any not new connections earlier
                                self.logger.info(f"First traffic detected from {src_ip}!")
                                                                
                                with self.lock:
                                    # Get or create device state
                                    if src_ip not in self.devices:
                                        if len(self.devices) >= self.max_devices:
                                            self.logger.warning(f"Max devices reached, ignoring {src_ip}")
                                            continue
                                        device = DeviceState(src_ip)
                                        device.detected = True
                                        device.first_seen = datetime.now()
                                        device.last_activity = datetime.now()
                                        self.devices[src_ip] = device
                                        self.logger.info(f"Added new device: {src_ip}")
                                    else:
                                        device = self.devices[src_ip]
                                        if not device.detected:
                                            device.detected = True
                                            device.first_seen = datetime.now()
                                        device.last_activity = datetime.now()
                                
                                    # Check if device should have 
                                
                                self._auth_sequence(device)
                                                            
                                ## self.get_device_rules(device)
                                             
                                # Apply rules for this device
                                ## self.update_device_rules(device)
                                ## self.update_traffic_rules(device)
                                ## self.update_shaping(device)
                                #self.clear_conntrack(device)
                                
                                ## self.save_state()
                                                                        
                                # Continue monitoring for other devices
                                # We don't terminate the process
                            
                            break  # Found src, no need to continue searching
                                
                except BlockingIOError:
                    time.sleep(0.1)
                    continue
                    
        except Exception as e:
            print(f"Monitor thread error: {e}")
        finally:
            # Cleanup conntrack process
            if self.conntrack_process:
                self.conntrack_process.terminate()
                try:
                    self.conntrack_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.conntrack_process.kill()
            print("Monitor thread exiting")
    
    def handle_overrides(self):
        self.logger.info(f"Handle overrides - looking for overrides in {self.overrides_file}")
        try:
            if os.path.exists(self.overrides_file):
                with open(self.overrides_file, 'r') as f:
                    data = json.load(f)
                    #print(data)                 
                    # Load devices
                    new_overrides = None
                    devices_data = data.get('devices', {})
                    for ip, override_data in devices_data.items():
                        self.logger.info(f"Found an override for {ip}")
                        if self.devices[ip] :
                            self.logger.info(f"Found the override in existing devices list {ip}")
                            device = self.devices[ip]
                            dev_dict = device.to_dict();
                            if dev_dict.get('redirect_rules_active') != override_data.get('redirect_rules_active'):
                                new_overrides = True
                                with self.lock:
                                    device.redirect_rules_active = override_data.get('redirect_rules_active')
                                                             
                    if new_overrides:
                        self.logger.info(f"Overrides implemented - Commit the changes")
                        self.update_device_rules(device)
                        self.update_traffic_rules(device)
                        self.save_state()        
                                              
        except Exception as e:
            self.logger.error(f"Error loading overrides: {e}")    
    
    def watch_overrides(self):
        """Watch for changes to the overrides and update rules accordingly"""
        print(f"Overrides watcher thread started (ID: {threading.get_ident()})")
        last_mtime = None
        
        while not self.shutdown_event.is_set():
            try:
                # Check if flag file exists and has been modified
                if os.path.exists(self.overrides_file):
                    current_mtime = os.path.getmtime(self.overrides_file)                   
                    if last_mtime is None or current_mtime != last_mtime:
                        last_mtime = current_mtime
                        self.logger.info(f"Overrides file changed launch action")
                        self.handle_overrides()
                        
                # Periodically check data and time caps
                self.check_data_time_caps()               
                
                # Periodically clean up inactive devices
                self.cleanup_inactive_devices()
                
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                self.logger.error(f"Error watching flag file: {e}")
                time.sleep(5)
    
    def _is_valid_ip(self,filename):    
        """Check if filename is a valid IP address"""
        try:
            ipaddress.ip_address(filename)
            return True
        except ValueError:
            return False            
                
    def monitor_re_auth_folder(self,folder_path="/var/lib/captive-portal/re-auth/"):
        """Monitor folder for IP-named files"""
        folder = Path(folder_path)
        folder.mkdir(parents=True, exist_ok=True)
        
        processed = set()
        
        while True:
            try:
                current_files = {f.name for f in folder.iterdir() if f.is_file()}
                new_files = current_files - processed
                
                for filename in new_files:
                    if self._is_valid_ip(filename):
                    
                        if filename in self.devices:
                            device = self.devices[filename]
                            print(f"---- Found {filename} in devices list ----")
                            self._auth_sequence(device)                      
                        print(f"Found IP: {filename}")                       
                        # Delete the file
                        file_path = folder / filename
                        file_path.unlink()
                        print(f"Deleted: {filename}")                       
                        processed.add(filename)
                
                # Clean up processed set
                processed = {f for f in processed if (folder / f).exists()}
                               
                time.sleep(1)
                
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(1)    
         
    def list_active_devices(self):
        """Return list of currently active devices"""
        with self.lock:
            active = []
            for ip, device in self.devices.items():
                if device.detected:
                    active.append({
                        'ip': ip,
                        'first_seen': device.first_seen.isoformat() if device.first_seen else None,
                        'last_activity': device.last_activity.isoformat() if device.last_activity else None,
                        'redirect_active': device.redirect_rules_active
                    })
            return active
            
    def run(self):
        """Main execution"""
        print("=" * 50)
        print("Simple Captive Portal")
        print("=" * 50)  
    
        """Main execution"""
        self.logger.info("Starting Captive Portal Controller (Multi-Device Mode)")
        self.logger.info(f"Monitoring subnet: {self.subnet}")
        self.logger.info(f"Redirect target: {self.redirect_ip}:{self.redirect_http_port} (HTTP) and :{self.redirect_https_port} (HTTPS)")
        self.logger.info(f"Device timeout: {self.device_timeout} seconds")
         
        # Create threads (daemon=True means they'll die with main thread)
        monitor_thread = threading.Thread(target=self.monitor_traffic, daemon=True)
        watcher_thread = threading.Thread(target=self.watch_overrides, daemon=True)
        
        re_auth_thread = threading.Thread(target=self.monitor_re_auth_folder, daemon=True)

  
        # Start threads
        monitor_thread.start()
        watcher_thread.start()
        re_auth_thread.start()
                  
        # Keep main thread alive but responsive to signals
        try:
            while not self.shutdown_event.is_set():
                self.shutdown_event.wait(timeout=1)
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received")
            self.shutdown_event.set()
        
        print("\nMain thread exiting (daemon threads will be terminated)")
        # No need to join daemon threads - they die when main thread exits
    
def show_devices():
    """Utility function to show current devices (can be called separately)"""
    controller = CaptivePortalController()
    active_devices = controller.list_active_devices()
    print(f"Active devices: {len(active_devices)}")
    for device in active_devices:
        print(f"  {device['ip']} - Redirect: {device['redirect_active']}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Captive Portal Controller for multiple devices')
    parser.add_argument('--show-devices', action='store_true', help='Show active devices and exit')
  
    args = parser.parse_args()
    
    if args.show_devices:
        show_devices()
        sys.exit(0)
    
    # Configuration
    controller = CaptivePortalController()
    
    # Handle graceful shutdown
    def signal_handler(sig, frame):
        logging.info("Shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
       
    controller.run()
