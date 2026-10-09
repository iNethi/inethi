import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import socket

# Configure logging
logger = logging.getLogger(__name__)

from libs.radius_attribute_helper import RADIUSAttributeHelper


class AccountingStatus(Enum):
    """Enum for accounting status types"""
    ON = "Accounting-On"
    OFF = "Accounting-Off"
    START = "Start"
    STOP = "Stop"
    INTERIM_UPDATE = "Interim-Update"


@dataclass
class AccountingResponse:
    """Standardized response dataclass"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None


class AccountingError(Exception):
    """Base exception for accounting errors"""
    pass


class RADIUSError(AccountingError):
    """RADIUS-specific errors"""
    pass


class AccountingHandler(ABC):
    """Abstract base class for accounting handlers"""
    
    @abstractmethod
    def send_accounting(
        self, 
        nas_info: Dict[str, Any], 
        status: AccountingStatus
    ) -> AccountingResponse:
        """Send accounting request with specified status"""
        pass
    
    @abstractmethod
    def accounting_on(
        self, 
        nas_info: Dict[str, Any]
    ) -> AccountingResponse:
        """Notify that NAS is up"""
        pass
    
    @abstractmethod
    def accounting_off(
        self, 
        nas_info: Dict[str, Any]
    ) -> AccountingResponse:
        """Notify that NAS is down"""
        pass
        
    @abstractmethod
    def accounting_start(
        self, 
        nas_info: Dict[str, Any]
    ) -> AccountingResponse:
        """Notify that user session is starting"""
        pass
        
    @abstractmethod
    def accounting_stop(
        self, 
        nas_info: Dict[str, Any]
    ) -> AccountingResponse:
        """Notify that user session has stopped"""
        pass
        
    @abstractmethod
    def accounting_update(
        self, 
        nas_info: Dict[str, Any]
    ) -> AccountingResponse:
        """Notify that user session has stopped"""
        pass
    
    
class RADIUSAccountingHandler(AccountingHandler):
    """RADIUS-based accounting implementation"""
    
    def __init__(
        self, 
        radius_server: str,
        radius_secret: str,
        radius_port: int = 1813,  # Standard RADIUS accounting port
        dictionary_path: str = "dictionary",
        timeout: int = 5,
        retries: int = 3
    ):
        self.radius_server = radius_server
        self.radius_secret = radius_secret.encode() if isinstance(radius_secret, str) else radius_secret
        self.radius_port = radius_port
        self.dictionary_path = dictionary_path
        self.timeout = timeout
        self.retries = retries
        
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
            raise AccountingError("pyrad library not installed") from e
    
    def _get_client(self):
        """Lazy initialization of RADIUS client"""
        if self._client is None:
            from pyrad.client import Client
            from pyrad.dictionary import Dictionary
            
            self._client = Client(
                server=self.radius_server,
                authport=self.radius_port,  # Use port parameter
                secret=self.radius_secret,
                dict=Dictionary(self.dictionary_path),
                timeout=self.timeout,
                retries=self.retries
            )
        return self._client
    
    def _validate_nas_info(self, nas_info: Dict[str, Any]) -> None:
        """Validate required NAS information fields"""
        required_fields = ["nas_ip_address", "nas_identifier"]
        missing_fields = [field for field in required_fields if field not in nas_info]
        
        if missing_fields:
            raise ValueError(f"Missing required NAS fields: {missing_fields}")
    
    def _create_accounting_packet(
        self, 
        nas_info: Dict[str, Any], 
        status: AccountingStatus
    ):
        """Create RADIUS accounting packet"""
        client = self._get_client()
        req = client.CreateAcctPacket()
        
        # Convert and add all attributes
        radius_attributes = RADIUSAttributeHelper.convert_attributes(nas_info)       
        radius_attributes['Acct-Status-Type'] = status.value
        
        # Add all converted attributes to the packet
        for key, value in radius_attributes.items():
            try:
                req[key] = value
            except Exception as e:
                logger.warning(f"Failed to add attribute {key}={value}: {e}")
            
        # Add message authenticator for security
        req.add_message_authenticator()
        
        return req
    
    def accounting_on(
        self, 
        nas_info: Dict[str, Any],
        additional_attributes: Optional[Dict[str, Any]] = None
    )-> AccountingResponse:
        """Send RADIUS accounting ON request"""
        
        # Merge NAS info with additional attributes
        attributes = {**nas_info}
        if additional_attributes:
            attributes.update(additional_attributes)
           
        return self.send_accounting(nas_info=attributes,status=AccountingStatus.ON)
        
    def accounting_off(
        self, 
        nas_info: Dict[str, Any],
        additional_attributes: Optional[Dict[str, Any]] = None
    )-> AccountingResponse:
        """Send RADIUS accounting ON request"""
        
        # Merge NAS info with additional attributes
        attributes = {**nas_info}
        if additional_attributes:
            attributes.update(additional_attributes)
            
        return self.send_accounting(nas_info=attributes,status=AccountingStatus.OFF)
        
        
    def accounting_start(
        self, 
        nas_info: Dict[str, Any],
        additional_attributes: Optional[Dict[str, Any]] = None
    )-> AccountingResponse:
        """Send RADIUS accounting START request"""
        
        # Merge NAS info with additional attributes
        attributes = {**nas_info}
        if additional_attributes:
            attributes.update(additional_attributes)
           
        return self.send_accounting(nas_info=attributes,status=AccountingStatus.START)            
    
    def accounting_stop(
        self, 
        nas_info: Dict[str, Any],
        additional_attributes: Optional[Dict[str, Any]] = None
    )-> AccountingResponse:
        """Send RADIUS accounting STOP request"""
        
        # Merge NAS info with additional attributes
        attributes = {**nas_info}
        if additional_attributes:
            attributes.update(additional_attributes)
           
        return self.send_accounting(nas_info=attributes,status=AccountingStatus.STOP)  
        
    def accounting_update(
        self, 
        nas_info: Dict[str, Any],
        additional_attributes: Optional[Dict[str, Any]] = None
    )-> AccountingResponse:
        """Send RADIUS accounting UPDATE request"""
        
        # Merge NAS info with additional attributes
        attributes = {**nas_info}
        if additional_attributes:
            attributes.update(additional_attributes)
           
        return self.send_accounting(nas_info=attributes,status=AccountingStatus.INTERIM_UPDATE)      
        
    def send_accounting(
        self, 
        nas_info: Dict[str, Any], 
        status: AccountingStatus
    ) -> AccountingResponse:
        """Send RADIUS accounting request"""
        try:
            import pyrad.packet
            from pyrad.client import Timeout
            
            self._validate_nas_info(nas_info)
            req = self._create_accounting_packet(nas_info, status)
            client = self._get_client()
            
            # Send packet with retry logic handled by pyrad
            reply = client.SendPacket(req)
            
            # Check response
            if reply.code == pyrad.packet.AccountingResponse:
                return AccountingResponse(
                    success=True,
                    message=f"RADIUS {status.value} accounting successful",
                    data={"reply_code": reply.code}
                )
            else:
                return AccountingResponse(
                    success=False,
                    message=f"RADIUS accounting failed with code: {reply.code}",
                    data={"reply_code": reply.code},
                    error_code="INVALID_RESPONSE"
                )
                
        except Timeout:
            logger.error(f"RADIUS timeout for {status.value} accounting")
            return AccountingResponse(
                success=False,
                message="RADIUS timeout",
                error_code="TIMEOUT"
            )
        except socket.error as e:
            logger.error(f"Network error in RADIUS accounting: {e}")
            return AccountingResponse(
                success=False,
                message="Network error",
                data={"network_error": str(e)},
                error_code="NETWORK_ERROR"
            )
        except Exception as e:
            logger.exception(f"Unexpected error in RADIUS accounting: {e}")
            return AccountingResponse(
                success=False,
                message=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR"
            )


class CaptivePortalAccounting:
    """Main accounting service with configurable handler"""
    
    def __init__(
        self,
        name: str = "Default Accounting",
        handler: Optional[AccountingHandler] = None
    ):
        self.name = name
        self._handler = handler
        logger.info(f"Initialized CaptivePortalAccounting '{name}' with handler: {type(handler).__name__ if handler else 'None'}")
    
    @property
    def handler(self) -> Optional[AccountingHandler]:
        """Get current handler"""
        return self._handler
    
    @handler.setter
    def handler(self, handler: AccountingHandler):
        """Set new handler with validation"""
        if not isinstance(handler, AccountingHandler):
            raise TypeError("Handler must implement AccountingHandler interface")
        self._handler = handler
        logger.info(f"Updated handler to {handler.__class__.__name__}")
    
    def accounting_on(self, nas_info: Dict[str, Any],additional_attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process accounting ON event"""
        if not self._handler:
            return self._create_error_response("No accounting handler configured")
        
        try:
            response = self._handler.accounting_on(nas_info,additional_attributes)
            return self._format_response(response)
        except Exception as e:
            logger.exception("Error in accounting_on")
            return self._create_error_response(f"Processing error: {str(e)}")
              
    def accounting_off(self, nas_info: Dict[str, Any],additional_attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process accounting OFF event"""
        if not self._handler:
            return self._create_error_response("No accounting handler configured")
        
        try:
            response = self._handler.accounting_off(nas_info,additional_attributes)
            return self._format_response(response)
        except Exception as e:
            logger.exception("Error in accounting_off")
            return self._create_error_response(f"Processing error: {str(e)}")
            
    def accounting_start(self, nas_info: Dict[str, Any],additional_attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process accounting START event"""
        if not self._handler:
            return self._create_error_response("No accounting handler configured")
        
        try:
            response = self._handler.accounting_start(nas_info,additional_attributes)
            return self._format_response(response)
        except Exception as e:
            logger.exception("Error in accounting_start")
            return self._create_error_response(f"Processing error: {str(e)}")
            
    def accounting_stop(self, nas_info: Dict[str, Any],additional_attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process accounting STOP event"""
        if not self._handler:
            return self._create_error_response("No accounting handler configured")
        
        try:
            response = self._handler.accounting_stop(nas_info,additional_attributes)
            return self._format_response(response)
        except Exception as e:
            logger.exception("Error in accounting_stop")
            return self._create_error_response(f"Processing error: {str(e)}")
    
    def accounting_update(self, nas_info: Dict[str, Any],additional_attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process accounting UPDATE event"""
        if not self._handler:
            return self._create_error_response("No accounting handler configured")
        
        try:
            response = self._handler.accounting_update(nas_info,additional_attributes)
            return self._format_response(response)
        except Exception as e:
            logger.exception("Error in accounting_stop")
            return self._create_error_response(f"Processing error: {str(e)}")   
    
    def _format_response(self, response: AccountingResponse) -> Dict[str, Any]:
        """Format response for external consumption"""
        return {
            'accounting_name': self.name,
            'success': response.success,
            'message': response.message,
            'data': response.data,
            'error_code': response.error_code
        }
    
    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            'accounting_name': self.name,
            'success': False,
            'message': message,
            'data': None,
            'error_code': 'HANDLER_ERROR'
        }
    
    def display_info(self) -> None:
        """Display accounting configuration information"""
        info = [
            f"\n{'='*50}",
            f"Captive Portal Accounting: {self.name}",
            f"{'='*50}",
            f"Handler Type: {self._handler.__class__.__name__ if self._handler else 'None'}",
            f"{'='*50}\n"
        ]
        print("\n".join(info))
        logger.info(f"Displayed info for accounting service '{self.name}'")
