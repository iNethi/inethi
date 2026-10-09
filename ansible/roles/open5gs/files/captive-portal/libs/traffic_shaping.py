# traffic_shaping.py
import subprocess
import logging
import json
from typing import Dict, Tuple, Optional, List

logger = logging.getLogger(__name__)

class TrafficShaping:
    """Impose and revoke bandwidth limits on IPs"""
    
    def __init__(self, 
        bw_iface    : str = 'br0',
        ifb_iface   : str = 'ifb0',
        bw_total    : str = '100mbit'   
    ):
        """
        Initialize the traffic shaping manager
        
        Args:
            bw_iface : The interface (LAN side or Tunnel) where shaping will take place  (default: br0)
            ifb_iface: The canonical way to shape ingress traffic - using an IFB interface (default: ifb0)
            bw_total : The total bandwidth available on the server (default: 100mbit)
        """
        
        self.bw_iface   = bw_iface
        self.ifb_iface  = ifb_iface
        self.bw_total   = bw_total
            
        self._prep_shaping()
        
    def add_ip_with_speed(self, ip : str, download : str, upload : str)-> bool:
        self.remove_ip(ip)
        hex_ip_id = self._hex_of_ip(ip)
        self._run(f"tc class add dev {self.bw_iface} parent 1:1 classid 1:{hex_ip_id} htb rate {download}")
        self._run(f"tc filter add dev {self.bw_iface} protocol ip parent 1:0 prio 1 u32  match ip dst {ip} flowid 1:{hex_ip_id}")
        
        self._run(f"tc class add dev {self.ifb_iface} parent 1:1 classid 1:{hex_ip_id} htb rate {upload}")
        self._run(f"tc filter add dev {self.ifb_iface} protocol ip parent 1:0 prio 1 u32  match ip src {ip} flowid 1:{hex_ip_id}")
        return True

    def remove_ip(self, ip: str) -> bool:

        #First the Main interface (egress - download)
        filters = self._get_tc_filters(self.bw_iface, "1:")
        matches = self._extract_u32_matches(filters)

        for m in matches:
            print(f"{m['direction']} {m['ip']} -> {m['flowid']}")
            self._run(f"tc filter del dev {self.bw_iface} protocol ip parent 1:0 prio 1 u32  match ip {m['direction']} {m['ip']} flowid {m['flowid']}")
            self._run(f"tc class del dev {self.bw_iface} classid {m['flowid']}")
          
        #Next the IFB interace that takes mirred ingress from main iterface as egress     
        filters = self._get_tc_filters(self.ifb_iface, "1:")
        matches = self._extract_u32_matches(filters)

        for m in matches:
            print(f"{m['direction']} {m['ip']} -> {m['flowid']}")
            self._run(f"tc filter del dev {self.ifb_iface} protocol ip parent 1:0 prio 1 u32  match ip {m['direction']} {m['ip']} flowid {m['flowid']}")
            self._run(f"tc class del dev {self.ifb_iface} classid {m['flowid']}")
            
        return True
    
    def _prep_shaping(self)-> None:
    
        #===== MAIN INTERFACE =====
    
        #We have to remove ingress and root on main interface
        result = subprocess.run(
            ["tc", "-j", "qdisc", "list", "dev", self.bw_iface],
            capture_output=True,
            text=True,
            check=True
        )
        res_tbl = json.loads(result.stdout)
        
        for qdisc in res_tbl:
            if qdisc.get('root'):
                if qdisc.get('kind') != 'noqueue':
                    self._run(f"tc qdisc del dev {self.bw_iface} root")
                    
            if qdisc.get('kind') == 'ingress':
                self._run(f"tc qdisc del dev {self.bw_iface} ingress")
                
        #Now we can create the initial setup on the main interface
        self._run(f"tc qdisc add dev {self.bw_iface} root handle 1: htb r2q 200")
        self._run(f"tc class add dev {self.bw_iface} parent 1: classid 1:1 htb rate {self.bw_total}")
        self._run(f"tc qdisc add dev {self.bw_iface} handle ffff: ingress")
        
        #Check if the IFB interface exist / if not add it
        try:
            subprocess.run(
                ["ip", "-j", "link", "list", self.ifb_iface],
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            self._run(f"modprobe ifb")
            self._run(f"ip link add {self.ifb_iface} type ifb")
            self._run(f"ip link set {self.ifb_iface} up")
        
        #Clean up IFB
        result_ifb = subprocess.run(
            ["tc", "-j", "qdisc", "list", "dev", self.ifb_iface],
            capture_output=True,
            text=True,
            check=True
        )
        res_ifb_tbl = json.loads(result_ifb.stdout)
        
        for qdisc in res_ifb_tbl:
            if qdisc.get('root'):
                if qdisc.get('kind') != 'fq_codel': #Here the default is fq_codel vs noqueue
                    self._run(f"tc qdisc del dev {self.ifb_iface} root")
              
        #Do the IFB Prep
        self._run(f"tc filter add dev {self.bw_iface} parent ffff: matchall action mirred egress redirect dev {self.ifb_iface}")
        self._run(f"tc qdisc add dev {self.ifb_iface} root handle 1: htb default 10 r2q 200")
        self._run(f"tc class add dev {self.ifb_iface} parent 1: classid 1:1 htb rate {self.bw_total}")
  
    def _get_tc_filters(self , dev: str, parent: str):
        """
        Returns parsed tc filter JSON for a given interface and parent.
        """
        result = subprocess.run(
            ["tc", "-j", "filter", "show", "dev", dev, "parent", parent],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)

    def _extract_u32_matches(self,filters):
        """
        Extracts IP match rules from tc filter JSON.
        Returns a list of dicts with direction + IP.
        """
        matches = []

        for f in filters:
            options = f.get("options", {})
            
            # u32 filters often nest match info here
            match = options.get("match")
            if not match:
                continue

            value = match.get("value")
            value = value.zfill(8)
            offset = match.get("off")

            if not value or offset is None:
                continue

            ip = self._tc_hex_to_ip(value)

            if offset == 12:
                direction = "src"
            elif offset == 16:
                direction = "dst"
            else:
                direction = f"unknown(offset={offset})"

            matches.append({
                "ip": ip,
                "direction": direction,
                "flowid": options.get("flowid"),
                "raw": match
            })

        return matches

    def _ip_to_tc_hex(self, ip: str) -> str:
        """
        Convert an IPv4 address (e.g. '172.16.0.102')
        into tc u32 hex format (e.g. 'ac100066').
        """
        octets = ip.split('.')
        
        if len(octets) != 4:
            raise ValueError("Invalid IPv4 address")

        try:
            return ''.join(f"{int(octet):02x}" for octet in octets)
        except ValueError:
            raise ValueError("Invalid IPv4 address")

    def _tc_hex_to_ip(self, hex_str: str) -> str:
        if len(hex_str) != 8:
            raise ValueError("Invalid tc hex string")

        return '.'.join(str(int(hex_str[i:i+2], 16)) for i in range(0, 8, 2))
  
    def _hex_of_ip(self,ip_address: str) -> str:
        """Generate unique flowid for an IP address (1:1 through 1:ffff)"""
        # Convert IP to integer for deterministic flowid
        parts = ip_address.split('.')
        
        if len(parts) == 4:
            ip_int = (int(parts[0]) << 24) | (int(parts[1]) << 16) | \
                     (int(parts[2]) << 8) | int(parts[3])
        else:
            # IPv6: use simple hash
            ip_int = hash(ip_address) & 0xFFFF
        
        # Flowid range: 1:1 to 1:FFFF (minor number = 1-65535)
        minor = (ip_int % 65534) + 1
        return hex(minor)
  
    def _run(self,cmd):
        try: 
            subprocess.run(cmd, shell=True, check=True,stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Error loading state: {e}")  
