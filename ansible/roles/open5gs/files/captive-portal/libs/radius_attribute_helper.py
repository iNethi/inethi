from typing import Dict, Any, Optional, Union, Tuple, List

class RADIUSAttributeHelper:
    """Helper class for RADIUS attribute name conversion and validation"""
    
    # Standard RADIUS attributes that should always be included
    STANDARD_ATTRIBUTES = {
        'nas_ip_address': 'NAS-IP-Address',
        'nas_identifier': 'NAS-Identifier',
        'service_type': 'Service-Type',
        'called_station_id': 'Called-Station-Id',
        'calling_station_id': 'Calling-Station-Id',
        'nas_port_type': 'NAS-Port-Type',
        'nas_port': 'NAS-Port',
        'nas_port_id': 'NAS-Port-Id',
        'framed_ip_address': 'Framed-IP-Address',
        'framed_ip_netmask': 'Framed-IP-Netmask',
        'filter_id': 'Filter-Id',
        'session_timeout': 'Session-Timeout',
        'idle_timeout': 'Idle-Timeout',
        'acct_session_id': 'Acct-Session-Id',
        'acct_session_time': 'Acct-Session-Time',
        'acct_input_octets' : 'Acct-Input-Octets',
        'acct_output_octets' : 'Acct-Output-Octets',
        'user_name': 'User-Name',
        'user_password': 'User-Password'
    }
    
    # Attributes that should be excluded from automatic conversion
    EXCLUDED_ATTRIBUTES = {
        'username',
        'password',
        'auth_type',
        'message_authenticator',
    }
    
    @classmethod
    def snake_to_radius(cls, snake_case: str) -> str:
        """
        Convert snake_case to RADIUS attribute format (Capitalized-Words-With-Hyphens)
        
        Examples:
            nas_ip_address -> NAS-IP-Address
            called_station_id -> Called-Station-Id
            wlan_ac_name -> WLAN-AC-Name
        """
        # Check if it's a known standard attribute
        if snake_case in cls.STANDARD_ATTRIBUTES:
            return cls.STANDARD_ATTRIBUTES[snake_case]
        
        # Split by underscore and capitalize each word
        words = snake_case.split('_')
        capitalized_words = [word.capitalize() for word in words]
        
        # Handle special cases like "IP" or "ID" that should be uppercase
        for i, word in enumerate(capitalized_words):
            if word.lower() in ['ip', 'id', 'mac', 'url', 'vlan', 'ssid', 'wlan', 'nas', 'acct']:
                capitalized_words[i] = word.upper()
            # Handle compound cases like "MSCHAP"
            elif word.lower() == 'mschap':
                capitalized_words[i] = 'MS-CHAP'
            elif word.lower() == 'mschapv2':
                capitalized_words[i] = 'MS-CHAP-V2'
        
        return '-'.join(capitalized_words)
    
    @classmethod
    def radius_to_snake(cls, radius_attr: str) -> str:
        """
        Convert RADIUS attribute format to snake_case
        
        Examples:
            NAS-IP-Address -> nas_ip_address
            Called-Station-Id -> called_station_id
        """
        # Replace hyphens with underscores and convert to lowercase
        return radius_attr.replace('-', '_').lower()
    
    @classmethod
    def convert_attributes(cls, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a dictionary of snake_case keys to RADIUS attribute format
        
        Args:
            attributes: Dictionary with snake_case keys
            
        Returns:
            Dictionary with RADIUS-formatted keys
        """
        converted = {}
        
        for key, value in attributes.items():
            # Skip excluded attributes
            if key in cls.EXCLUDED_ATTRIBUTES:
                continue
                
            # Handle nested dictionaries recursively
            if isinstance(value, dict):
                value = cls.convert_attributes(value)
            
            # Convert the key
            radius_key = cls.snake_to_radius(key)
            converted[radius_key] = value
        
        return converted
    
    @classmethod
    def extract_attributes(cls, radius_packet, snake_case: bool = True) -> Dict[str, Any]:
        """
        Extract attributes from a RADIUS packet and optionally convert to snake_case
        
        Args:
            radius_packet: PyRAD packet object
            snake_case: If True, convert keys to snake_case format
            
        Returns:
            Dictionary of attributes
        """
        
        attributes = {}
        
        for attr_name in radius_packet.keys():
            values = radius_packet[attr_name]
            valid_values = [x for x in values if isinstance(x, (str, int)) and not isinstance(x, (bool,bytes))]
            if valid_values:
                if snake_case:
                    attr_name = cls.radius_to_snake(attr_name)
                attributes[attr_name] = valid_values
                   
        return attributes