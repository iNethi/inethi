import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, Tuple, List
from dataclasses import dataclass
from enum import Enum
import socket

# Configure logging
logger = logging.getLogger(__name__)

from libs.radius_attribute_helper import RADIUSAttributeHelper


class AuthenticationStatus(Enum):
    """Enum for authentication status types"""
    ACCEPT = "Access-Accept"
    REJECT = "Access-Reject"
    CHALLENGE = "Access-Challenge"


class AuthType(Enum):
    """Enum for authentication types"""
    PAP = "PAP"
    CHAP = "CHAP"
    MSCHAP = "MS-CHAP"
    MSCHAPV2 = "MS-CHAP-V2"
    EAP = "EAP"


@dataclass
class AuthenticationResponse:
    """Standardized authentication response dataclass"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    session_id: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None


class AuthenticationError(Exception):
    """Base exception for authentication errors"""
    pass


class RADIUSAuthenticationError(AuthenticationError):
    """RADIUS-specific authentication errors"""
    pass


class AuthenticationHandler(ABC):
    """Abstract base class for authentication handlers"""
    
    @abstractmethod
    def authenticate(
        self, 
        username: str,
        password: str,
        nas_info: Dict[str, Any],
        auth_type: AuthType = AuthType.PAP
    ) -> AuthenticationResponse:
        """Authenticate user with specified credentials"""
        pass
    
    @abstractmethod
    def authorize(
        self,
        username: str,
        nas_info: Dict[str, Any],
        attributes: Optional[Dict[str, Any]] = None
    ) -> AuthenticationResponse:
        """Authorize user access (without password validation)"""
        pass


class RADIUSAuthenticationHandler(AuthenticationHandler):
    """RADIUS-based authentication implementation"""
    
    def __init__(
        self, 
        radius_server: str,
        radius_secret: str,
        radius_auth_port: int = 1812,  # Standard RADIUS authentication port
        radius_acct_port: int = 1813,
        dictionary_path: str = "dictionary",
        timeout: int = 5,
        retries: int = 3,
        default_service_type: str = "Login-User"
    ):
        self.radius_server = radius_server
        self.radius_secret = radius_secret.encode() if isinstance(radius_secret, str) else radius_secret
        self.radius_auth_port = radius_auth_port
        self.radius_acct_port = radius_acct_port
        self.dictionary_path = dictionary_path
        self.timeout = timeout
        self.retries = retries
        self.default_service_type = default_service_type
        
        # Lazy import and validation
        self._client = None
        self._validate_imports()
    
    def _validate_imports(self) -> None:
        """Validate that required libraries are available"""
        try:
            import pyrad.packet
            from pyrad.client import Client
            from pyrad.dictionary import Dictionary
            self._pyrad_available = True
        except ImportError as e:
            self._pyrad_available = False
            logger.error("pyrad library not installed. Install with: pip install pyrad")
            raise AuthenticationError("pyrad library not installed") from e
    
    def _get_client(self):
        """Lazy initialization of RADIUS client"""
        if self._client is None:
            from pyrad.client import Client
            from pyrad.dictionary import Dictionary
            
            self._client = Client(
                server=self.radius_server,
                authport=self.radius_auth_port,
                acctport=self.radius_acct_port,
                secret=self.radius_secret,
                dict=Dictionary(self.dictionary_path),
                timeout=self.timeout,
                retries=self.retries
            )
        return self._client
    
    def _validate_required_attributes(self, attributes: Dict[str, Any]) -> None:
        """Validate that required attributes are present"""
        required_attrs = ['nas_ip_address', 'nas_identifier']
        missing_attrs = [attr for attr in required_attrs if attr not in attributes]
        
        if missing_attrs:
            raise ValueError(f"Missing required attributes: {missing_attrs}")
    
    def _create_auth_packet(
        self, 
        username: str,
        password: str,
        attributes: Dict[str, Any],
        auth_type: AuthType
    ):
        """Create RADIUS authentication packet with flexible attributes"""
        import pyrad.packet
        client = self._get_client()
      
        # Create base packet
        if auth_type == AuthType.PAP:
            req = client.CreateAuthPacket(
                code=pyrad.packet.AccessRequest,
                User_Name=username
            )
            req["User-Password"] = req.PwCrypt(password)
        elif auth_type == AuthType.CHAP:
            req = client.CreateAuthPacket(
                code=pyrad.packet.AccessRequest,
                User_Name=username
            )
            # CHAP specific handling would go here
            req["CHAP-Password"] = password
        else:
            raise ValueError(f"Unsupported authentication type: {auth_type}")
        
        # Convert and add all attributes
        radius_attributes = RADIUSAttributeHelper.convert_attributes(attributes)
        
        # Ensure Service-Type is set
        if 'Service-Type' not in radius_attributes:
            radius_attributes['Service-Type'] = self.default_service_type
        
        # Add all converted attributes to the packet
        for key, value in radius_attributes.items():
            try:
                req[key] = value
            except Exception as e:
                logger.warning(f"Failed to add attribute {key}={value}: {e}")
        
        # Add message authenticator for security
        req.add_message_authenticator()
        
        return req
    
    def authenticate(
        self, 
        username: str,
        password: str,
        nas_info: Dict[str, Any],
        auth_type: AuthType = AuthType.PAP,
        additional_attributes: Optional[Dict[str, Any]] = None
    ) -> AuthenticationResponse:
        """
        Authenticate user with RADIUS server
        
        Args:
            username: User's username
            password: User's password
            nas_info: Dictionary of NAS/network attributes (will be converted to RADIUS format)
            auth_type: Authentication type (PAP, CHAP, etc.)
            additional_attributes: Any additional attributes to include in the request
        """
        try:
            import pyrad.packet
            from pyrad.client import Timeout
            
            if not username or not password:
                return AuthenticationResponse(
                    success=False,
                    message="Username and password are required",
                    error_code="MISSING_CREDENTIALS"
                )
            
            # Merge NAS info with additional attributes
            attributes = {**nas_info}
            if additional_attributes:
                attributes.update(additional_attributes)
            
            # Validate required attributes
            self._validate_required_attributes(attributes)
            
            # Create and send packet
            req = self._create_auth_packet(username, password, attributes, auth_type)
            client = self._get_client()
            
            # Send packet with retry logic handled by pyrad
            reply = client.SendPacket(req)
            
            # Extract attributes and session ID
            response_attributes = RADIUSAttributeHelper.extract_attributes(reply)
            session_id = None
            
            if 'class' in response_attributes:
                class_value = response_attributes['class']
                session_id = class_value[0] if isinstance(class_value, list) else class_value
            
            # Check response
            if reply.code == pyrad.packet.AccessAccept:
                return AuthenticationResponse(
                    success=True,
                    message=f"Authentication successful for user: {username}",
                    data={
                        "reply_code": reply.code, 
                        "auth_type": auth_type.value,
                        "attributes_sent": list(attributes.keys())
                    },
                    session_id=session_id,
                    attributes=response_attributes
                )
            elif reply.code == pyrad.packet.AccessReject:
                return AuthenticationResponse(
                    success=False,
                    message=f"Authentication rejected for user: {username}",
                    data={"reply_code": reply.code, "auth_type": auth_type.value},
                    error_code="ACCESS_REJECT",
                    attributes=response_attributes
                )
            elif reply.code == pyrad.packet.AccessChallenge:
                return AuthenticationResponse(
                    success=False,
                    message=f"Authentication challenge required for user: {username}",
                    data={"reply_code": reply.code, "auth_type": auth_type.value},
                    error_code="ACCESS_CHALLENGE",
                    attributes=response_attributes
                )
            else:
                return AuthenticationResponse(
                    success=False,
                    message=f"Unexpected response code: {reply.code}",
                    data={"reply_code": reply.code},
                    error_code="UNEXPECTED_RESPONSE"
                )
                
        except Timeout:
            logger.error(f"RADIUS timeout for user: {username}")
            return AuthenticationResponse(
                success=False,
                message="RADIUS authentication timeout",
                error_code="TIMEOUT"
            )
        except socket.error as e:
            logger.error(f"Network error in RADIUS authentication: {e}")
            return AuthenticationResponse(
                success=False,
                message="Network error",
                data={"network_error": str(e)},
                error_code="NETWORK_ERROR"
            )
        except Exception as e:
            logger.exception(f"Unexpected error in RADIUS authentication: {e}")
            return AuthenticationResponse(
                success=False,
                message=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR"
            )
    
    def authorize(
        self,
        username: str,
        nas_info: Dict[str, Any],
        attributes: Optional[Dict[str, Any]] = None
    ) -> AuthenticationResponse:
        """Authorize user without password validation"""
        try:
            import pyrad.packet
            from pyrad.client import Timeout
            
            if not username:
                return AuthenticationResponse(
                    success=False,
                    message="Username is required",
                    error_code="MISSING_USERNAME"
                )
            
            self._validate_required_attributes(nas_info)
            
            client = self._get_client()
            req = client.CreateAuthPacket(
                code=pyrad.packet.AccessRequest,
                User_Name=username
            )
            
            # Merge and convert attributes
            all_attributes = {**nas_info}
            if attributes:
                all_attributes.update(attributes)
            
            all_attributes['service_type'] = "Authorize-Only"
            radius_attributes = RADIUSAttributeHelper.convert_attributes(all_attributes)
            
            # Add all attributes to packet
            for key, value in radius_attributes.items():
                try:
                    req[key] = value
                except Exception as e:
                    logger.warning(f"Failed to add attribute {key}={value}: {e}")
            
            # Add message authenticator
            req.add_message_authenticator()
            
            # Send packet
            reply = client.SendPacket(req)
            
            # Extract response attributes
            response_attributes = RADIUSAttributeHelper.extract_attributes(reply)
            
            if reply.code == pyrad.packet.AccessAccept:
                return AuthenticationResponse(
                    success=True,
                    message=f"Authorization successful for user: {username}",
                    data={"reply_code": reply.code},
                    attributes=response_attributes
                )
            else:
                return AuthenticationResponse(
                    success=False,
                    message=f"Authorization failed for user: {username}",
                    data={"reply_code": reply.code},
                    error_code="AUTHORIZATION_FAILED",
                    attributes=response_attributes
                )
                
        except Exception as e:
            logger.exception(f"Error in authorization: {e}")
            return AuthenticationResponse(
                success=False,
                message=f"Authorization error: {str(e)}",
                error_code="AUTHORIZATION_ERROR"
            )

class LocalAuthenticationHandler(AuthenticationHandler):
    """Local authentication implementation for testing/fallback"""
    
    def __init__(self, user_database: Optional[Dict[str, str]] = None):
        self.user_database = user_database or {}
        logger.info("Initialized LocalAuthenticationHandler")
    
    def authenticate(
        self, 
        username: str,
        password: str,
        nas_info: Dict[str, Any],
        auth_type: AuthType = AuthType.PAP,
        additional_attributes: Optional[Dict[str, Any]] = None
    ) -> AuthenticationResponse:
        """Authenticate against local user database"""
        try:
            if not username or not password:
                return AuthenticationResponse(
                    success=False,
                    message="Username and password are required",
                    error_code="MISSING_CREDENTIALS"
                )
            
            if username in self.user_database:
                stored_password = self.user_database[username]
                if stored_password == password:
                    # Create response attributes from nas_info
                    attributes = RADIUSAttributeHelper.convert_attributes(nas_info)
                    
                    return AuthenticationResponse(
                        success=True,
                        message=f"Local authentication successful for user: {username}",
                        data={
                            "auth_type": auth_type.value,
                            "nas_info": nas_info
                        },
                        session_id=f"LOCAL_{username}_{id(self)}",
                        attributes=attributes
                    )
            
            return AuthenticationResponse(
                success=False,
                message=f"Local authentication failed for user: {username}",
                error_code="INVALID_CREDENTIALS"
            )
            
        except Exception as e:
            logger.exception(f"Error in local authentication: {e}")
            return AuthenticationResponse(
                success=False,
                message=f"Local authentication error: {str(e)}",
                error_code="LOCAL_AUTH_ERROR"
            )
    
    def authorize(
        self,
        username: str,
        nas_info: Dict[str, Any],
        attributes: Optional[Dict[str, Any]] = None
    ) -> AuthenticationResponse:
        """Simple authorization for local handler"""
        if username in self.user_database:
            return AuthenticationResponse(
                success=True,
                message=f"Local authorization successful for user: {username}",
                data={"authorized": True, "nas_info": nas_info}
            )
        
        return AuthenticationResponse(
            success=False,
            message=f"Local authorization failed for user: {username}",
            error_code="USER_NOT_FOUND"
        )


class CaptivePortalAuthentication:
    """Main authentication service with configurable handler"""
    
    def __init__(
        self,
        name: str = "Default Authentication",
        handler: Optional[AuthenticationHandler] = None,
        session_manager: Optional[Any] = None
    ):
        self.name = name
        self._handler = handler
        self.session_manager = session_manager
        logger.info(f"Initialized CaptivePortalAuthentication '{name}' with handler: {type(handler).__name__ if handler else 'None'}")
    
    @property
    def handler(self) -> Optional[AuthenticationHandler]:
        """Get current handler"""
        return self._handler
    
    @handler.setter
    def handler(self, handler: AuthenticationHandler):
        """Set new handler with validation"""
        if not isinstance(handler, AuthenticationHandler):
            raise TypeError("Handler must implement AuthenticationHandler interface")
        self._handler = handler
        logger.info(f"Updated handler to {handler.__class__.__name__}")
    
    def authenticate(
        self,
        username: str,
        password: str,
        nas_info: Dict[str, Any],
        auth_type: AuthType = AuthType.PAP,
        additional_attributes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process authentication request"""
        if not self._handler:
            return self._create_error_response("No authentication handler configured")
        
        try:
            response = self._handler.authenticate(
                username, password, nas_info, auth_type, additional_attributes
            )
            
            # Create session if authentication successful and session manager available
            if response.success and self.session_manager:
                session_data = {
                    'username': username,
                    'nas_info': nas_info,
                    'auth_type': auth_type.value,
                    'attributes': response.attributes,
                    'additional_attributes': additional_attributes
                }
                session_id = self.session_manager.create_session(session_data)
                response.session_id = session_id
            
            return self._format_response(response)
        except Exception as e:
            logger.exception("Error in authenticate")
            return self._create_error_response(f"Processing error: {str(e)}")
    
    def authorize(
        self,
        username: str,
        nas_info: Dict[str, Any],
        attributes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process authorization request"""
        if not self._handler:
            return self._create_error_response("No authentication handler configured")
        
        try:
            response = self._handler.authorize(username, nas_info, attributes)
            return self._format_response(response)
        except Exception as e:
            logger.exception("Error in authorize")
            return self._create_error_response(f"Processing error: {str(e)}")
    
    def _format_response(self, response: AuthenticationResponse) -> Dict[str, Any]:
        """Format response for external consumption"""
        return {
            'auth_name': self.name,
            'success': response.success,
            'message': response.message,
            'data': response.data,
            'error_code': response.error_code,
            'session_id': response.session_id,
            'attributes': response.attributes
        }
    
    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            'auth_name': self.name,
            'success': False,
            'message': message,
            'data': None,
            'error_code': 'HANDLER_ERROR',
            'session_id': None,
            'attributes': None
        }
    
    def display_info(self) -> None:
        """Display authentication configuration information"""
        info = [
            f"\n{'='*50}",
            f"Captive Portal Authentication: {self.name}",
            f"{'='*50}",
            f"Handler Type: {self._handler.__class__.__name__ if self._handler else 'None'}",
            f"Session Manager: {'Enabled' if self.session_manager else 'Disabled'}",
            f"{'='*50}\n"
        ]
        print("\n".join(info))
        logger.info(f"Displayed info for authentication service '{self.name}'")


# Example usage demonstrating the flexible attribute system
if __name__ == "__main__":
    # Example showing automatic attribute conversion
    radius_auth = RADIUSAuthenticationHandler(
        radius_server="192.168.1.100",
        radius_secret="secret123",
        timeout=5
    )
    
    auth_service = CaptivePortalAuthentication(
        name="Flexible WiFi Auth",
        handler=radius_auth
    )
    
    # Now you can include ANY attributes - they'll be automatically converted!
    nas_info = {
        "nas_ip_address": "192.168.1.1",
        "nas_identifier": "AP01-MainLobby",
        "called_station_id": "00-11-22-33-44-55",
        "calling_station_id": "AA-BB-CC-DD-EE-FF",
        "nas_port_type": "Wireless-802.11",
        "wlan_ac_name": "AC-Controller-01",  # Will become WLAN-AC-Name
        "wlan_user_priority": 5,  # Will become WLAN-User-Priority
        "ssid": "Guest-WiFi",  # Will become SSID
        "vlan_id": 100,  # Will become VLAN-ID
        "location_name": "Main_Lobby_Floor_1",  # Will become Location-Name
        "some_custom_attribute": "custom_value"  # Will become Some-Custom-Attribute
    }
    
    # Additional attributes can be passed separately
    additional_attrs = {
        "acct_interim_interval": 300,  # Will become Acct-Interim-Interval
        "session_timeout": 3600,  # Will become Session-Timeout
        "idle_timeout": 600,  # Will become Idle-Timeout
    }
    
    result = auth_service.authenticate(
        username="guest_user",
        password="guest_pass123",
        nas_info=nas_info,
        additional_attributes=additional_attrs
    )
    
    print("Authentication Result:")
    print(json.dumps(result, indent=2))
    
    # Test the attribute conversion directly
    print("\nAttribute Conversion Test:")
    test_attrs = {
        "my_custom_radius_attr": "value1",
        "another_attr_with_ip": "192.168.1.1",
        "mschap_v2_data": "some_data",
        "wlan_signal_strength": -65,
        "user_agent_string": "Mozilla/5.0"
    }
    
    converted = RADIUSAttributeHelper.convert_attributes(test_attrs)
    print(f"Original: {json.dumps(test_attrs, indent=2)}")
    print(f"Converted: {json.dumps(converted, indent=2)}")
    
    auth_service.display_info()
