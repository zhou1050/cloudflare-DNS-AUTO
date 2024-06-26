import socket
import requests
import time

# Configuration
MAIN_IP = "1.1.1.1"
MAIN_PORT = 24153
BACKUP_IPS = [
    "2.2.2.2",
    "3.3.3.3"
]
NUM_ATTEMPTS = 3  # 每个备用 IP 尝试的次数

# Cloudflare Configuration
CFKEY = "7d33c1704d"
CFUSER = "1822.com"
CFZONE_NAME = "xx.xyz"
CFRECORD_NAME = "zz.xyz"
CFTTL = 120

def is_tcp_port_open(ip, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # 设置连接超时时间为5秒
        result = sock.connect_ex((ip, port))
        if result == 0:
            return True  # 端口是开放的
        else:
            return False  # 端口是关闭的
    except Exception as e:
        print(f"Exception occurred while checking TCP port: {e}")
        return False
    finally:
        sock.close()

def update_dns_record(new_ip):
    try:
        # 获取 Cloudflare 的 Zone ID 和 Record ID
        zone_id, record_id = get_zone_and_record_ids()

        if zone_id and record_id:
            # 更新 DNS 记录到新的 IP
            response = requests.put(
                f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}",
                headers={
                    "X-Auth-Email": CFUSER,
                    "X-Auth-Key": CFKEY,
                    "Content-Type": "application/json"
                },
                json={
                    "type": "A",
                    "name": CFRECORD_NAME,
                    "content": new_ip,
                    "ttl": CFTTL
                }
            )

            if response.status_code == 200 and response.json().get("success", False):
                print(f"DNS record updated successfully to {new_ip}")
            else:
                print(f"Failed to update DNS record to {new_ip}")
                print(response.text)
        else:
            print("Failed to retrieve Zone ID and Record ID. DNS record update aborted.")

    except Exception as e:
        print(f"Exception occurred during DNS update: {e}")

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
        zone_id = response.json()["result"][0]["id"]
        
        response = requests.get(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?name={CFRECORD_NAME}",
            headers={
                "X-Auth-Email": CFUSER,
                "X-Auth-Key": CFKEY,
                "Content-Type": "application/json"
            }
        )
        record_id = response.json()["result"][0]["id"]
        
        return zone_id, record_id

    except Exception as e:
        print(f"Exception occurred while retrieving Zone ID and Record ID: {e}")
        return None, None

def main_loop():
    while True:
        # 检测主 IP 是否可用
        if is_tcp_port_open(MAIN_IP, MAIN_PORT):
            print(f"Service is up at {MAIN_IP}:{MAIN_PORT}. No DNS record update required.")
        else:
            print(f"Main service at {MAIN_IP}:{MAIN_PORT} is down. Trying backup IPs...")

            # 依次检测备用 IP
            for backup_ip in BACKUP_IPS:
                for attempt in range(NUM_ATTEMPTS):
                    if is_tcp_port_open(backup_ip, MAIN_PORT):
                        print(f"Service is up at {backup_ip}:{MAIN_PORT}. Updating DNS record...")
                        update_dns_record(backup_ip)
                        break  # 找到可用的备用 IP 后更新 DNS 记录并退出当前备用 IP 的检测
                    else:
                        print(f"Attempt {attempt + 1}: Service at {backup_ip}:{MAIN_PORT} is down.")

                # 如果找到可用的备用 IP，则不再继续检测其他备用 IP
                if is_tcp_port_open(backup_ip, MAIN_PORT):
                    break

        time.sleep(60)  # 每隔60秒执行一次检测

if __name__ == "__main__":
    main_loop()
