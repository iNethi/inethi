#!/usr/bin/python
from pyrad import dictionary, packet, server
import logging
import os
import configparser
import atexit
                   
class PodServer(server.Server):

    def HandleAuthPacket(self, pkt):
        pass
        
    def HandleAcctPacket(self, pkt):
        pass

    def HandleCoaPacket(self, pkt):
        pass

    def HandleDisconnectPacket(self, pkt):

        logger = logging.getLogger(__name__)
        logger.info("Received a disconnect request")
        
        if pkt['Framed-IP-Address'] :
            ip = pkt['Framed-IP-Address'][0]
            
            # Create the directory if it doesn't exist
            reauth_dir = "/var/lib/captive-portal/re-auth"
            if not os.path.exists(reauth_dir):
                os.makedirs(reauth_dir)
            
            # Create an empty file with the IP address as the name
            file_path = os.path.join(reauth_dir, ip)
            try:
                with open(file_path, 'w') as f:
                    pass  # This creates an empty file
                logger.info(f"Created empty file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to create file {file_path}: {e}")

        reply = self.CreateReplyPacket(pkt)
        # Disconnect-ACK
        reply.code = 41
        self.SendReplyPacket(pkt.fd, reply)

def cleanup(srv):
    """Properly clean up server resources"""
    logging.info("Cleaning up resources...")
    if hasattr(srv, 'socket') and srv.socket:
        try:
            srv.socket.close()
        except Exception as e:
            logging.debug(f"Error closing socket: {e}")


if __name__ == '__main__':

    config      = configparser.ConfigParser()
    config.read(['/etc/captive-portal/pod_server.conf'])
       
    log_level_s = config.get('podserver', 'log_level', fallback='INFO').upper()
    log_level   = getattr(logging, log_level_s, logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/var/log/captive-portal/pod_server.log'),
            logging.StreamHandler()
        ]
    )
         
    ip          = config.get('podsender', 'ip_address')       
    secret      = config.get('podsender', 'shared_secret').encode() # Get secret as string, then encode to bytes
    pod_name    = config.get('podsender', 'name')   

    # create server and read dictionary
    srv         = PodServer(dict=dictionary.Dictionary("/opt/captive-portal/radius_dictionaries/dictionary"), auth_enabled=False, acct_enabled=False, coa_enabled=True)      
    pod_srv     = config.get('podserver', 'bind_to_ip')
      
    # add clients (address, secret, name)
    srv.hosts[ip] = server.RemoteHost(ip, secret, pod_name)
    srv.BindToAddress(pod_srv)
   
    atexit.register(cleanup, srv)  # Will run on any exit

    try:
        srv.Run()
    except KeyboardInterrupt:
        pass  # atexit handles it
        
