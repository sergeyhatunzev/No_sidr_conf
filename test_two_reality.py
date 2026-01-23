import subprocess
import time
import socket
import requests
import os
import psutil

# ================== НАСТРОЙКИ ==================
PORT = 1080                     # порт socks5 в конфигах
TEST_URL = "https://www.google.com/generate_204"
TIMEOUT = 12                    # секунд на запрос
MAX_STARTUP_WAIT = 15.0         # секунд на запуск xray
POLL_INTERVAL = 0.2             # шаг проверки порта

XRAY_PATH = "xray"              # или "xray.exe" / полный путь
# XRAY_PATH = r"./xray"         # пример, если лежит рядом

# ================== ДВА КОНФИГА (как строки) ==================

CONFIG_SWEDEN = """{
  "log": {"loglevel": "warning"},
  "inbounds": [
    {
      "port": 1080,
      "listen": "127.0.0.1",
      "protocol": "socks",
      "settings": {"udp": false}
    }
  ],
  "outbounds": [
    {
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "150.241.65.72",
            "port": 443,
            "users": [
              {
                "id": "f79aba55-5300-4da4-9dbf-0db09e57b57a",
                "encryption": "none",
                "flow": "xtls-rprx-vision"
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "publicKey": "cRyfPg-_KmYl_kPBrsxCP6Yodugb6vs4jDEBmswxtVI",
          "shortId": "",
          "serverName": "max.ru",
          "fingerprint": "chrome",
          "spiderX": "/"
        }
      }
    }
  ],
  "routing": {
    "rules": [
      {
        "type": "field",
        "inboundTag": ["inbound"],
        "outboundTag": "outbound"
      }
    ]
  }
}"""

CONFIG_NETHERLANDS = """{
  "log": {"loglevel": "warning"},
  "inbounds": [
    {
      "port": 1080,
      "listen": "127.0.0.1",
      "protocol": "socks",
      "settings": {"udp": false}
    }
  ],
  "outbounds": [
    {
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "144.31.224.141",
            "port": 443,
            "users": [
              {
                "id": "f79aba55-5300-4da4-9dbf-0db09e57b57a",
                "encryption": "none",
                "flow": "xtls-rprx-vision"
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "publicKey": "cRyfPg-_KmYl_kPBrsxCP6Yodugb6vs4jDEBmswxtVI",
          "shortId": "",
          "serverName": "max.ru",
          "fingerprint": "chrome",
          "spiderX": "/"
        }
      }
    }
  ],
  "routing": {
    "rules": [
      {
        "type": "field",
        "inboundTag": ["inbound"],
        "outboundTag": "outbound"
      }
    ]
  }
}"""

CONFIGS = [
    ("Sweden 150.241.65.72", CONFIG_SWEDEN),
    ("Netherlands 144.31.224.141", CONFIG_NETHERLANDS)
]

# ================== ФУНКЦИИ ==================

def is_port_open(port):
    try:
        with socket.socket() as s:
            s.settimeout(0.3)
            return s.connect_ex(('127.0.0.1', port)) == 0
    except:
        return False

def kill_proc(proc):
    if not proc:
        return
    try:
        proc.kill()
        if psutil.pid_exists(proc.pid):
            for child in psutil.Process(proc.pid).children(recursive=True):
                child.kill()
    except:
        pass

def test_one_config(name, config_str):
    print(f"\n=== Тест: {name} ===")

    temp_file = f"temp_{name.replace(' ', '_')}.json"
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(config_str)

    try:
        proc = subprocess.Popen(
            [XRAY_PATH, "run", "-c", temp_file],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL   # ← поменяй на sys.stdout, если хочешь видеть логи
        )
    except Exception as e:
        print(f"Ошибка запуска Xray: {e}")
        return

    # Ожидание порта
    start = time.time()
    opened = False
    while time.time() - start < MAX_STARTUP_WAIT:
        if is_port_open(PORT):
            opened = True
            break
        time.sleep(POLL_INTERVAL)

    if not opened:
        print(f"Порт {PORT} не открылся за {MAX_STARTUP_WAIT} сек → Xray не стартовал")
        kill_proc(proc)
        os.remove(temp_file)
        return

    print(f"Порт {PORT} открыт через {time.time() - start:.1f} сек")

    time.sleep(1.2)  # даём время на handshake

    # Проверка соединения
    proxies = {'http': f'socks5://127.0.0.1:{PORT}', 'https': f'socks5://127.0.0.1:{PORT}'}

    try:
        t0 = time.time()
        r = requests.get(TEST_URL, proxies=proxies, timeout=TIMEOUT, verify=False)
        ms = round((time.time() - t0) * 1000)
        if r.status_code == 204:
            print(f"→ LIVE   {ms:4} мс")
        else:
            print(f"→ ????   HTTP {r.status_code}   ({ms} мс)")
    except Exception as e:
        print(f"→ DEAD   {type(e).__name__}: {str(e)[:70]}")

    kill_proc(proc)
    time.sleep(0.5)
    try:
        os.remove(temp_file)
    except:
        pass

# ================== ЗАПУСК ==================

if __name__ == "__main__":
    if not os.path.isfile(XRAY_PATH) and not os.path.isfile(XRAY_PATH + ".exe"):
        print(f"Xray не найден: {XRAY_PATH}")
        print("Положи xray / xray.exe рядом или укажи полный путь")
    else:
        for name, cfg in CONFIGS:
            test_one_config(name, cfg)
            time.sleep(2)  # пауза между тестами
        print("\nТест завершён.")
