# get_config.py

import requests
from requests.auth import HTTPDigestAuth

CAMERA_IP = "192.168.80.173"
USERNAME = "admin"
PASSWORD = "user12345"

# Используем базовый URL БЕЗ ID, чтобы получить весь список хостов
url = f"http://{CAMERA_IP}/ISAPI/Event/notification/httpHosts"
auth = HTTPDigestAuth(USERNAME, PASSWORD)

try:
    print(f"Отправка GET-запроса на: {url}")
    response = requests.get(url, auth=auth)
    response.raise_for_status()
    
    print("\nУСПЕХ! Текущая конфигурация httpHosts получена.")
    print("="*50)
    print(response.text)
    print("="*50)

except requests.exceptions.RequestException as e:
    print(f"Ошибка: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"Статус код: {e.response.status_code}")
        print(f"Тело ответа: {e.response.text}") 

 