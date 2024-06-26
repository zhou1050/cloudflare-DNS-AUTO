import time
import logging
import requests

# Cloudflare API credentials
CFKEY = "YOUR_CF_API_KEY"
CFUSER = "YOUR_CF_EMAIL"
CFZONE_NAME = "example.com"
CFRECORD_NAME = "www.example.com"
CFRECORD_TYPE = "A"
CFTTL = 120

# Main and backup IPs
MAIN_IP = "3.3.3.3"
MAIN_PORT = 24153
BACKUP_IPS = [
    "1.1.1.1",
    "2.2.2.2"
]

# Telegram Bot credentials (optional for notifications)
TG_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TG_CHATID = "YOUR_TELEGRAM_CHAT_ID"

# Ping API to check service availability
PING_API = f"http://{MAIN_IP}:{MAIN_PORT}/ping"

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def is_service_up(ip, port):
    try:
        response = requests.get(f"http://{ip}:{port}/ping")
        return response.status_code == 200
    except requests.RequestException as e:
        logging.error(f"Error checking service at {ip}:{port}: {str(e)}")
        return False

def update_dns_record(ip):
    try:
        zone_id, record_id = get_zone_and_record_ids()
        if zone_id and record_id:
            response = requests.put(
                f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}",
                headers={
                    "X-Auth-Email": CFUSER,
                    "X-Auth-Key": CFKEY,
                    "Content-Type": "application/json"
                },
                json={
                    "type": CFRECORD_TYPE,
                    "name": CFRECORD_NAME,
                    "content": ip,
                    "ttl": CFTTL
                }
            )
            if response.ok:
                logging.info(f"Updated DNS record for {CFRECORD_NAME} to {ip}")
                return True
            else:
                logging.error(f"Failed to update DNS record: {response.text}")
                return False
        else:
            logging.error("Failed to retrieve Zone ID and Record ID. DNS record update aborted.")
            return False
    except Exception as e:
        logging.error(f"Exception occurred during DNS update: {str(e)}")
        return False

def get_zone_and_record_ids():
    try:
        response = requests.get(
            f"https://api.cloudflare.com/client/v4/zones?name={CFZONE_NAME}",
            headers={
                "X-Auth-Email": CFUSER,
                "X-Auth-Key": CFKEY,
                "Content-Type": "application/json"
            }
        )
        data = response.json()
        zone_id = data["result"][0]["id"]
        
        response = requests.get(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type={CFRECORD_TYPE}&name={CFRECORD_NAME}",
            headers={
                "X-Auth-Email": CFUSER,
                "X-Auth-Key": CFKEY,
                "Content-Type": "application/json"
            }
        )
        data = response.json()
        record_id = data["result"][0]["id"]
        
        return zone_id, record_id
    except Exception as e:
        logging.error(f"Exception occurred while retrieving Zone ID and Record ID: {str(e)}")
        return None, None

def main_loop():
    use_backup_ip = False
    
    while True:
        try:
            if is_service_up(MAIN_IP, MAIN_PORT):
                if use_backup_ip:
                    logging.info(f"Main service at {MAIN_IP}:{MAIN_PORT} is up. Switching back to main IP.")
                    update_dns_record(MAIN_IP)
                    use_backup_ip = False
            else:
                logging.warning(f"Main service at {MAIN_IP}:{MAIN_PORT} is down. Trying backup IPs...")
                
                for ip in BACKUP_IPS:
                    if is_service_up(ip, MAIN_PORT):
                        logging.info(f"Service is up at {ip}:{MAIN_PORT}. Updating DNS record...")
                        update_dns_record(ip)
                        use_backup_ip = True
                        break
                    else:
                        logging.warning(f"Service at {ip}:{MAIN_PORT} is down.")

            time.sleep(60)  # 每隔60秒执行一次检测
        except KeyboardInterrupt:
            logging.info("Script terminated by user.")
            break
        except Exception as e:
            logging.error(f"Unhandled exception in main loop: {str(e)}")
            time.sleep(60)  # 等待一段时间后继续执行

if __name__ == "__main__":
    main_loop()

