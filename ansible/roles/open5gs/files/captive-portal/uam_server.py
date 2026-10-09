from flask import Flask, redirect, request
from flask import render_template
import configparser
import logging
import threading
import signal
import sys

app = Flask(__name__)

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    redirect_ip = app.config.get('REDIRECT_IP')
    http_port = app.config.get('HTTP_PORT')
    return redirect(f"http://{redirect_ip}:{http_port}/portal", code=302)

@app.route("/portal")
def portal():
    return render_template("portal.html")

def run_http():
    try:
        app.run(host=app.config['REDIRECT_IP'], port=app.config['HTTP_PORT'])
    except Exception as e:
        logging.info(f"HTTP server stopped: {e}")

def run_https():
    try:
        app.run(host=app.config['REDIRECT_IP'], port=app.config['HTTPS_PORT'], 
                ssl_context=("cert.pem", "key.pem"))
    except Exception as e:
        logging.info(f"HTTPS server stopped: {e}")

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read(['/etc/captive-portal/captive_portal.conf'])
    
    log_level_s = config.get('captive_portal', 'log_level', fallback='INFO').upper()
    log_level = getattr(logging, log_level_s, logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/var/log/captive-portal/uam_server.log'),
            logging.StreamHandler()
        ]
    )
    
    app.config['REDIRECT_IP'] = config.get('captive_portal', 'redirect_ip', fallback="172.16.0.1")
    app.config['HTTP_PORT'] = int(config.get('captive_portal', 'redirect_http_port', fallback="3990"))
    app.config['HTTPS_PORT'] = int(config.get('captive_portal', 'redirect_https_port', fallback="4990"))
    
    # Set up signal handlers for graceful shutdown
    stop_event = threading.Event()
    
    def signal_handler(sig, frame):
        logging.info("Shutting down gracefully...")
        stop_event.set()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    t1 = threading.Thread(target=run_http, daemon=True)
    t2 = threading.Thread(target=run_https, daemon=True)
    
    t1.start()
    t2.start()
    
    try:
        while not stop_event.is_set():
            stop_event.wait(1)
    except KeyboardInterrupt:
        logging.info("Received shutdown signal")