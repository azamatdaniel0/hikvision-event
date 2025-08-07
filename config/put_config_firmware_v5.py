# put_config.py (ФИНАЛЬНАЯ ВЕРСИЯ)
import requests
from requests.auth import HTTPDigestAuth

CAMERA_IP = "192.168.80.173"
USERNAME = "admin"  
PASSWORD = "user12345"
HIKVISION_HTTP_HOSTS_URL = f"http://{CAMERA_IP}/ISAPI/Event/notification/httpHosts"

# --- НАШИ НАСТРОЙКИ ---
ID = '1'                     # ID хоста, который мы хотим настроить (1, 2 или 3)
IP = '192.168.80.112'        # IP-адрес нашего сервера
PORT = '8785'                # Порт нашего сервера
URL_PATH = '/firmware_v5'      # Путь на нашем сервере, куда придут события

def put_config():
    # --- СОБИРАЕМ XML ТОЧНО ПО ШАБЛОНУ, ПОЛУЧЕННОМУ ОТ КАМЕРЫ ---
    data = f"""<?xml version="1.0" encoding="UTF-8"?>
<HttpHostNotification version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
    <id>{ID}</id>
    <url>{URL_PATH}</url>
    <protocolType>HTTP</protocolType>
    <parameterFormatType>XML</parameterFormatType>
    <addressingFormatType>ipaddress</addressingFormatType>
    <ipAddress>{IP}</ipAddress>
    <portNo>{PORT}</portNo>
    <userName></userName>
    <httpAuthenticationMethod>none</httpAuthenticationMethod>
    <httpBroken>true</httpBroken>
    <ANPR>
        <detectionUpLoadPicturesType>all</detectionUpLoadPicturesType>
    </ANPR>
</HttpHostNotification>
"""
    
    # URL для отправки PUT-запроса (обновляем хост с конкретным ID)
    config_url_with_id = f"{HIKVISION_HTTP_HOSTS_URL}/{ID}"
    
    try:
        print(f"Отправка PUT-запроса на URL: {config_url_with_id}")
        
        # Для отладки выведем XML, который отправляем
        print("\n--- Отправляемый XML ---")
        print(data.strip())
        print("------------------------\n")

        response = requests.put(
            url=config_url_with_id,
            auth=HTTPDigestAuth(USERNAME, PASSWORD),
            data=data.strip(),
            headers={'Content-Type': 'application/xml'},
            timeout=15
        )
        response.raise_for_status()

        print(f"УСПЕХ! Настройка HTTP-хоста прошла успешно! Статус код: {response.status_code}")
        print("Ответ камеры:")
        print(response.text)

        # Проверочный GET-запрос, чтобы убедиться, что настройки сохранились
        print("\nПроверка сохраненных настроек...")
        check_response = requests.get(config_url_with_id, auth=HTTPDigestAuth(USERNAME, PASSWORD))
        print(check_response.text)

    except requests.exceptions.RequestException as e:
        print(f"ОШИБКА при настройке HTTP-хоста: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Статус код: {e.response.status_code}")
            print(f"Тело ответа: {e.response.text}")

if __name__ == "__main__":
    put_config()