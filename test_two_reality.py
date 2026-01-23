import subprocess
import time
import socket
import requests
import os
import json
import sys
import psutil
from datetime import datetime

# ================== НАСТРОЙКИ ==================
TEST_PORT = 1080                # порт socks5 в конфиге
TEST_URL = "https://www.google.com/generate_204"  # или "https://1.1.1.1", "https://connectivitycheck.gstatic.com/generate_204"
TIMEOUT_SEC = 15                # таймаут на запрос
STARTUP_WAIT_MAX = 12.0         # максимум секунд на запуск xray
POLL_INTERVAL = 0.15            # шаг проверки порта

XRAY_PATH = "xray"              # или "xray.exe", или полный путь
# XRAY_PATH = r"C:\tools\xray\xray.exe"   # пример для Windows

# ================== ДВА КОНФИГА ==================

CONFIG_1 = """{
  "log": {"loglevel": "warning"},
  "inbounds": [
    {
      "port": 1080,
      "listen": "127.0.0.1",
      "protocol": "socks",
      "tag": "in_1080",
      "settings": {"udp": false}
    }
  ],
  "outbounds": [
    {
      "protocol": "vless",
      "tag": "out_1080",
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
        "inboundTag": ["in_1080"],
        "outboundTag": "out_1080"
      }
    ],
    "domainStrategy": "AsIs"
  }
}"""

CONFIG_2 = """{
  "log": {"loglevel": "warning"},
  "inbounds": [
    {
      "port": 1080,
      "listen": "127.0.0.1",
      "protocol": "socks",
      "tag": "in_1080",
      "settings": {"udp": false}
    }
  ],
  "outbounds": [
    {
      "protocol": "vless",
      "tag": "out_1080",
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
        "inboundTag": ["in_1080"],
        "outboundTag": "out_1080"
      }
    ],
    "domainStrategy": "AsIs"
  }
}"""

# ================== ФУНКЦИИ ==================

def is_port_open(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            return s.connect_ex(('127.0.0.1', port)) == 0
    except:
        return False

def kill_process(proc):
    if not proc:
        return
    try:
        proc.kill()
        if psutil.pid_exists(proc.pid):
            parent = psutil.Process(proc.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
    except:
        pass

def test_config(config_json_str, label):
    print(f"\n{'='*60}")
    print(f"Тест: {label}")
    print(f"Время запуска: {datetime.now().strftime('%H:%M:%S')}")
    print('='*60)

    # Создаём временный файл конфига
    temp_config = f"temp_{label.replace(' ', '_')}.json"
    with open(temp_config, "w", encoding="utf-8") as f:
        f.write(config_json_str)

    # Запускаем xray
    cmd = [XRAY_PATH, "run", "-c", temp_config]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,   # можно убрать DEVNULL и увидеть логи
            # stderr=subprocess.STDOUT,
            # stdout=sys.stdout,          # раскомментировать для живых логов
        )
    except Exception as e:
        print(f"Ошибка запуска xray: {e}")
        return

    # Ждём открытия порта
    started = False
    start_time = time.time()
    for _ in range(int(STARTUP_WAIT_MAX / POLL_INTERVAL)):
        if is_port_open(TEST_PORT):
            started = True
            break
        time.sleep(POLL_INTERVAL)

    if not started:
        print(f"Порт {TEST_PORT} не открылся за {STARTUP_WAIT_MAX} сек → таймаут запуска")
        kill_process(proc)
        try:
            os.remove(temp_config)
        except:
            pass
        return

    print(f"Порт {TEST_PORT} открыт через {time.time() - start_time:.2f} сек")

    # Даём ещё 1–2 секунды на установку соединения
    time.sleep(1.8)

    # Тестируем соединение
    proxies = {
        'http': f'socks5://127.0.0.1:{TEST_PORT}',
        'https': f'socks5://127.0.0.1:{TEST_PORT}'
    }

    try:
        t_start = time.time()
        r = requests.get(TEST_URL, proxies=proxies, timeout=TIMEOUT_SEC, verify=False)
        latency = round((time.time() - t_start) * 1000)

        if r.status_code == 204:
            print(f"[ LIVE ] Задержка: {latency:4} мс    статус: {r.status_code}")
        else:
            print(f"[ ???? ] Задержка: {latency:4} мс    статус: HTTP {r.status_code}")

    except requests.exceptions.ConnectTimeout:
        print("[ DEAD ] ConnectTimeout")
    except requests.exceptions.ReadTimeout:
        print("[ DEAD ] ReadTimeout")
    except Exception as e:
        print(f"[ DEAD ] {type(e).__name__}: {str(e)[:80]}")

    # Убиваем процесс и чистим
    kill_process(proc)
    time.sleep(0.4)
    try:
        os.remove(temp_config)
    except:
        pass

# ================== ЗАПУСК ТЕСТОВ ==================

if __name__ == "__main__":
    if not os.path.exists(XRAY_PATH) and not XRAY_PATH.endswith(".exe"):
        print(f"Xray не найден по пути: {XRAY_PATH}")
        print("Укажите правильный XRAY_PATH в начале скрипта")
        sys.exit(1)

    test_config(CONFIG_1, "Sweden 150.241.65.72")
    time.sleep(2)  # пауза между тестами
    test_config(CONFIG_2, "Netherlands 144.31.224.141")

    print("\nТестирование завершено.")
