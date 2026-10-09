#!/usr/bin/env python3
import subprocess
import sys
import re
import logging

# Configure logging at module level
logger = logging.getLogger(__name__)

class WalledGardenManager:
    def __init__(self, ipset_name="walled_garden_list", source_subnet="172.16.0.0/16"):
        self.ipset_name = ipset_name
        self.source_subnet = source_subnet
        self.entries = []
        logger.debug(f"Initialized WalledGardenManager with ipset={ipset_name}, subnet={source_subnet}")
    
    def _run(self, cmd, check=True, capture=True):
        """Internal command runner with error handling."""
        logger.debug(f"Executing command: {cmd}")
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                check=check,
                capture_output=capture,
                text=True
            )
            if result.returncode == 0:
                logger.debug(f"Command succeeded: {cmd}")
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {cmd}")
            logger.error(f"Error output: {e.stderr.strip()}")
            if check:
                raise
            return e
    
    def add_entry(self, ip_or_subnet):
        """Add an IP or subnet to the walled garden list."""
        self.entries.append(ip_or_subnet)
        logger.info(f"Added entry to walled garden list: {ip_or_subnet}")
    
    def add_entries(self, entries_list):
        """Add multiple entries at once."""
        self.entries.extend(entries_list)
        logger.info(f"Added {len(entries_list)} entries to walled garden list")
        logger.debug(f"Entries added: {entries_list}")
    
    def create_ipset(self, force_recreate=True):
        """Create the ipset."""
        if force_recreate:
            logger.info(f"Destroying existing ipset (if any): {self.ipset_name}")
            # Destroy existing set if it exists
            result = self._run(f"ipset destroy {self.ipset_name}", check=False)
            if result.returncode == 0:
                logger.info(f"Destroyed existing ipset: {self.ipset_name}")
            else:
                logger.debug(f"No existing ipset found to destroy: {self.ipset_name}")
        
        # Create new ipset
        logger.info(f"Creating ipset: {self.ipset_name}")
        result = self._run(f"ipset create {self.ipset_name} hash:net")
        
        if result.returncode == 0:
            logger.info(f"✓ Successfully created ipset: {self.ipset_name}")
            return True
        else:
            logger.error(f"✗ Failed to create ipset: {self.ipset_name}")
            return False
    
    def populate_ipset(self):
        """Add all entries to the ipset."""
        if not self.entries:
            logger.warning("No entries to add to ipset!")
            return False
        
        logger.info(f"Populating ipset with {len(self.entries)} entries")
        success_count = 0
        
        for entry in self.entries:
            result = self._run(f"ipset add {self.ipset_name} {entry}", check=False)
            if result.returncode == 0:
                success_count += 1
                logger.debug(f"✓ Added {entry} to ipset")
            else:
                logger.error(f"✗ Failed to add {entry} to ipset: {result.stderr.strip() if hasattr(result, 'stderr') else 'Unknown error'}")
        
        logger.info(f"Successfully added {success_count}/{len(self.entries)} entries to ipset")
        return success_count == len(self.entries)
        
    def insert_prerouting_bypass(self, position=1):
        """Add PREROUTING bypass for entire subnet (no redirect for walled garden)."""
        cmd = (
            f"iptables -t nat -I PREROUTING {position} "
            f"-s {self.source_subnet} "
            f"-m set --match-set {self.ipset_name} dst "
            f"-j RETURN"
        )
        
        logger.info(f"Adding PREROUTING bypass for {self.source_subnet}")
        result = self._run(cmd)
        
        if result.returncode == 0:
            logger.info(f"✓ PREROUTING bypass added at position {position}")
            return True
        else:
            logger.error(f"✗ Failed to add PREROUTING bypass")
            return False
    
    def insert_iptables_rule(self, position=1):
        """Insert iptables rule at specified position."""
        cmd = (
            f"iptables -I FORWARD {position} "
            f"-s {self.source_subnet} "
            f"-m set --match-set {self.ipset_name} dst "
            f"-j ACCEPT"
        )
        
        logger.info(f"Inserting iptables rule at position {position}")
        logger.debug(f"Full iptables command: {cmd}")
        
        result = self._run(cmd)
        
        if result.returncode == 0:
            logger.info(f"✓ Successfully inserted iptables rule at position {position}")
            return True
        else:
            logger.error(f"✗ Failed to insert iptables rule")
            return False
    
    def verify_rules(self):
        """Verify the ipset and iptables rules are active."""
        logger.info("=== Verifying walled garden configuration ===")
        
        # Check ipset exists
        result = self._run(f"ipset list {self.ipset_name}", check=False)
        if result.returncode == 0:
            # Extract number of entries
            match = re.search(r"Number of entries:\s+(\d+)", result.stdout)
            count = match.group(1) if match else "unknown"
            logger.info(f"✓ ipset '{self.ipset_name}' exists with {count} entries")
            logger.debug(f"Full ipset output:\n{result.stdout}")
        else:
            logger.error(f"✗ ipset '{self.ipset_name}' not found")
            return False
        
        # Check iptables rule
        result = self._run(f"iptables -L FORWARD -n", check=False)
        if self.ipset_name in result.stdout:
            logger.info(f"✓ iptables rule found for '{self.ipset_name}'")
            # Get the specific rule with line number
            rule_result = self._run(f"iptables -L FORWARD -n -v --line-numbers | grep {self.ipset_name}", check=False)
            if rule_result.returncode == 0:
                logger.debug(f"Rule details:\n{rule_result.stdout}")
            return True
        else:
            logger.warning(f"✗ iptables rule for '{self.ipset_name}' not found")
            return False
    
    def cleanup(self):
        """Remove all rules and ipset."""
        logger.info("=== Starting cleanup ===")
        
        # Remove FORWARD rule
        logger.info(f"Removing FORWARD rule")
        result = self._run(
            f"iptables -D FORWARD -s {self.source_subnet} "
            f"-m set --match-set {self.ipset_name} dst -j ACCEPT",
            check=False
        )
        
        # Remove PREROUTING bypass
        logger.info(f"Removing PREROUTING bypass")
        result = self._run(
            f"iptables -t nat -D PREROUTING "
            f"-s {self.source_subnet} "
            f"-m set --match-set {self.ipset_name} dst "
            f"-j RETURN",
            check=False
        )
        
        # Destroy ipset
        logger.info(f"Destroying ipset: {self.ipset_name}")
        self._run(f"ipset destroy {self.ipset_name}", check=False)
        
        logger.info("Cleanup complete")
    
    
    def get_rule_count(self):
        """Get the number of entries in the ipset."""
        result = self._run(f"ipset list {self.ipset_name} | grep 'Number of entries'", check=False)
        if result.returncode == 0:
            match = re.search(r"(\d+)", result.stdout)
            if match:
                return int(match.group(1))
        return 0
    
    def list_entries(self):
        """List all entries in the walled garden ipset."""
        result = self._run(f"ipset list {self.ipset_name}", check=False)
        if result.returncode == 0:
            logger.info(f"Current entries in {self.ipset_name}:")
            lines = result.stdout.split('\n')
            in_members = False
            for line in lines:
                if 'Members:' in line:
                    in_members = True
                elif in_members and line.strip():
                    logger.info(f"  {line.strip()}")
        return result.returncode == 0

# Example usage with different logging configurations
if __name__ == "__main__":
    # Check root privileges
    if subprocess.run("id -u", shell=True, capture_output=True, text=True).stdout.strip() != "0":
        print("❌ This script must be run as root (use sudo)", file=sys.stderr)
        sys.exit(1)
    
    # Configure logging to show INFO level and above to console
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create manager
    wg = WalledGardenManager(
        ipset_name="walled_garden_list",
        source_subnet="172.16.0.0/16"
    )
    
    wg.cleanup()
    
    # Add walled garden entries
    wg.add_entries([
        "8.8.8.8",
        "8.8.4.4",
        "1.1.1.1",
        "192.168.1.0/24",
        "208.67.222.222",  # OpenDNS
        "208.67.220.220",  # OpenDNS
    ])
    
    # Setup
    wg.create_ipset(force_recreate=True)
    wg.populate_ipset()
    
    wg.insert_iptables_rule(position=1)
    wg.insert_prerouting_bypass(position=1)
      
    wg.verify_rules()
    
    # Optional: List entries
    wg.list_entries()
    
    # Optional: If you want to test cleanup, uncomment:
    # wg.cleanup()
