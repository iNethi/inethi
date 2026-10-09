# traffic_accounting.py
import subprocess
import logging
import json
from typing import Dict, Tuple, Optional, List

logger = logging.getLogger(__name__)

class TrafficAccounting:
    """Manages nfacct-based traffic accounting for captive portal IPs"""
    
    def __init__(self, subnet: str = "172.16.0.0/24"):
        """
        Initialize the traffic accounting manager
        
        Args:
            subnet: The subnet to monitor (default: 172.16.0.0/24)
        """
        self.subnet = subnet
        self._validate_nfacct()
    
    def _validate_nfacct(self) -> None:
        """Check if nfacct is available on the system"""
        result = self._run_cmd("which nfacct", ignore_errors=True)
        if result.returncode != 0:
            raise RuntimeError("nfacct command not found. Please install nfacct package.")
    
    def _run_cmd(self, cmd: str, ignore_errors: bool = False) -> subprocess.CompletedProcess:
        """Run a shell command with sudo prefix"""
        full_cmd = f"sudo {cmd}" if not cmd.startswith("sudo") else cmd
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0 and not ignore_errors:
            logger.error(f"Command failed: {full_cmd}")
            logger.error(f"Error: {result.stderr}")
        
        return result
    
    def _get_accounting_names(self, ip: str) -> Tuple[str, str]:
        """Get the inbound and outbound accounting names for an IP"""
        ip_clean = ip.replace('.', '_')
        return f"ip_{ip_clean}_out", f"ip_{ip_clean}_in"
    
    def add_ip(self, ip: str) -> bool:
        """
        Add accounting rules for a specific IP
        
        Args:
            ip: The IP address to track
            
        Returns:
            True if successful, False otherwise
        """
        out_name, in_name = self._get_accounting_names(ip)
        
        try:
            # Check and add nfacct objects
            nfacct_list = self._run_cmd("nfacct list", ignore_errors=True)
            existing_nfacct = nfacct_list.stdout if nfacct_list.returncode == 0 else ""
            
            if out_name not in existing_nfacct:
                self._run_cmd(f"nfacct add {out_name}")
                logger.debug(f"Added nfacct object: {out_name}")
            else:
                logger.debug(f"nfacct object {out_name} already exists, skipping")
            
            if in_name not in existing_nfacct:
                self._run_cmd(f"nfacct add {in_name}")
                logger.debug(f"Added nfacct object: {in_name}")
            else:
                logger.debug(f"nfacct object {in_name} already exists, skipping")
            
            # Check and add iptables rules using iptables -C
            # Outbound rule (source IP)
            check_cmd_out = f"iptables -C FORWARD -s {ip} -m nfacct --nfacct-name {out_name}"
            result_out = self._run_cmd(check_cmd_out, ignore_errors=True)
            
            if result_out.returncode != 0:  # Rule doesn't exist
                self._run_cmd(f"iptables -I FORWARD -s {ip} -m nfacct --nfacct-name {out_name}")
                logger.debug(f"Added iptables rule for {out_name}")
            else:
                logger.debug(f"iptables rule for {out_name} already exists, skipping")
            
            # Inbound rule (destination IP)
            check_cmd_in = f"iptables -C FORWARD -d {ip} -m nfacct --nfacct-name {in_name}"
            result_in = self._run_cmd(check_cmd_in, ignore_errors=True)
            
            if result_in.returncode != 0:  # Rule doesn't exist
                self._run_cmd(f"iptables -I FORWARD -d {ip} -m nfacct --nfacct-name {in_name}")
                logger.debug(f"Added iptables rule for {in_name}")
            else:
                logger.debug(f"iptables rule for {in_name} already exists, skipping")
            
            logger.info(f"Added accounting for {ip}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add accounting for {ip}: {e}")
            return False   
    
    def remove_ip(self, ip: str) -> bool:
        """
        Remove accounting rules for a specific IP
        
        Args:
            ip: The IP address to stop tracking
            
        Returns:
            True if successful, False otherwise
        """
        out_name, in_name = self._get_accounting_names(ip)
        
        try:
            # Remove iptables rules
            self._run_cmd(f"iptables -D FORWARD -s {ip} -m nfacct --nfacct-name {out_name}", ignore_errors=True)
            self._run_cmd(f"iptables -D FORWARD -d {ip} -m nfacct --nfacct-name {in_name}", ignore_errors=True)
            
            # Delete accounting objects
            self._run_cmd(f"nfacct delete {out_name}", ignore_errors=True)
            self._run_cmd(f"nfacct delete {in_name}", ignore_errors=True)
            
            logger.info(f"Removed accounting for {ip}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove accounting for {ip}: {e}")
            return False
    
    def get_bytes(self, ip):
        """Get byte counts for an IP using JSON output"""
        out_name = f"ip_{ip.replace('.', '_')}_out"
        in_name = f"ip_{ip.replace('.', '_')}_in"
        
        bytes_out = self._get_nfacct_json(out_name)
        bytes_in = self._get_nfacct_json(in_name)
        
        return {
            'bytes_in': bytes_in, 
            'bytes_out': bytes_out, 
            'total': bytes_in + bytes_out
        }
    
    def _get_nfacct_json(self, name):
        """Get nfacct counter using JSON output"""
        result = subprocess.run(
            f"nfacct get {name} json", 
            shell=True, 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0 and result.stdout:
            try:
                data = json.loads(result.stdout)
                # Navigate the JSON structure
                if 'nfacct_counters' in data and len(data['nfacct_counters']) > 0:
                    return int(data['nfacct_counters'][0]['bytes'])
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                logger.error(f"Failed to parse JSON for {name}: {e}")
        
        return 0
    
    def get_full_json(self, ip):
        """Get complete JSON response for debugging"""
        out_name = f"ip_{ip.replace('.', '_')}_out"
        in_name = f"ip_{ip.replace('.', '_')}_in"
        
        result_out = subprocess.run(f"nfacct get {out_name} json", shell=True, capture_output=True, text=True)
        result_in = subprocess.run(f"nfacct get {in_name} json", shell=True, capture_output=True, text=True)
        
        return {
            'out': json.loads(result_out.stdout) if result_out.stdout else {},
            'in': json.loads(result_in.stdout) if result_in.stdout else {}
        }
    
    def get_formatted_bytes(self, ip):
        """Get human readable format"""
        bytes_data = self.get_bytes(ip)
        return {
            'bytes_in': self._format_bytes(bytes_data['bytes_in']),
            'bytes_out': self._format_bytes(bytes_data['bytes_out']),
            'total': self._format_bytes(bytes_data['total'])
        }
    
    def _format_bytes(self, bytes_count):
        """Convert bytes to human readable"""
        if bytes_count == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} TB"
    
    def get_all_ips(self):
        """Get all IPs with accounting using JSON"""
        result = subprocess.run("nfacct list json", shell=True, capture_output=True, text=True)
        ips = []
        
        if result.returncode == 0 and result.stdout:
            try:
                data = json.loads(result.stdout)
                # Parse the list output
                # You might need to adjust this based on actual output format
                if 'nfacct_counters' in data:
                    for counter in data['nfacct_counters']:
                        name = counter.get('name', '')
                        if name.startswith('ip_') and name.endswith('_out'):
                            # Extract IP from name
                            ip_part = name.replace('ip_', '').replace('_out', '')
                            ip = ip_part.replace('_', '.')
                            ips.append(ip)
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to parse JSON list: {e}")
        
        return list(set(ips))  # Remove duplicates
    
    def reset_ip(self, ip: str) -> bool:
        """
        Reset counters for an IP (remove and re-add)
        
        Args:
            ip: The IP address to reset
            
        Returns:
            True if successful, False otherwise
        """
        if self.remove_ip(ip):
            return self.add_ip(ip)
        return False
    
    def ip_exists(self, ip: str) -> bool:
        """
        Check if accounting exists for an IP
        
        Args:
            ip: The IP address to check
            
        Returns:
            True if accounting exists, False otherwise
        """
        out_name, _ = self._get_accounting_names(ip)
        result = self._run_cmd(f"nfacct get {out_name}", ignore_errors=True)
        return result.returncode == 0
    
   
    def cleanup_all(self) -> bool:
        """
        Remove all accounting rules for all tracked IPs
        
        Returns:
            True if successful, False otherwise
        """
        ips = self.get_all_ips()
        success = True
        
        for ip in ips:
            if not self.remove_ip(ip):
                success = False
        
        logger.info(f"Cleaned up accounting for {len(ips)} IPs")
        return success
    
    def check_quota(self, ip: str, max_bytes: int) -> Tuple[bool, Dict[str, int]]:
        """
        Check if an IP has exceeded its quota
        
        Args:
            ip: The IP address to check
            max_bytes: Maximum allowed bytes (total in+out)
            
        Returns:
            Tuple of (is_within_quota, bytes_data)
        """
        bytes_data = self.get_bytes(ip)
        is_within = bytes_data['bytes_total'] <= max_bytes
        
        if not is_within:
            logger.warning(f"IP {ip} exceeded quota: {bytes_data['bytes_total']}/{max_bytes} bytes")
        
        return is_within, bytes_data
