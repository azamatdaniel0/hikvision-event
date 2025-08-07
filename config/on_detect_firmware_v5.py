import requests
from requests.auth import HTTPDigestAuth

# --- НАСТРОЙКИ ---
CAMERA_IP = "192.168.80.173"
USERNAME = "admin"
PASSWORD = "user12345"
url = f"http://{CAMERA_IP}/ISAPI/System/Video/inputs/channels/1/motionDetection"
auth = HTTPDigestAuth(USERNAME, PASSWORD)
headers = {'Content-Type': 'application/xml'}


try:
    # --- ШАГ 1: ПОЛУЧАЕМ ТЕКУЩУЮ КОНФИГУРАЦИЮ (GET) ---
    print("1. Получение текущей конфигурации...")
    get_response = requests.get(url, auth=auth)
    get_response.raise_for_status() # Проверяем, что GET-запрос прошел успешно
    
    original_xml = get_response.text
    print("   Текущий статус <enabled>:", "true" if "<enabled>true</enabled>" in original_xml else "false")


    # --- ШАГ 2: МОДИФИЦИРУЕМ XML ---
    print("2. Модификация XML для включения детекции движения...")
    # Просто заменяем подстроку
    modified_xml = original_xml.replace("<enabled>false</enabled>", "<enabled>true</enabled>")

    if modified_xml == original_xml:
        print("   Внимание: Детекция движения уже была включена, изменений не требуется.")
    else:
        print("   XML успешно изменен.")


    # --- ШАГ 3: ОТПРАВЛЯЕМ НОВУЮ КОНФИГУРАЦИЮ (PUT) ---
    print("3. Отправка новой конфигурации на камеру...")
    put_response = requests.put(url, data=modified_xml.encode('utf-8'), auth=auth, headers=headers)
    
    # Проверяем ответ от PUT-запроса
    if put_response.status_code == 200:
        print("\nУСПЕХ! Конфигурация успешно применена. Статус код: 200")
        
        # --- ШАГ 4 (ПРОВЕРОЧНЫЙ): СНОВА ЗАПРАШИВАЕМ КОНФИГУРАЦИЮ ---
        print("4. Повторная проверка статуса на камере...")
        final_check_response = requests.get(url, auth=auth)
        final_xml = final_check_response.text
        
        if "<enabled>true</enabled>" in final_xml:
            print("   ПОДТВЕРЖДЕНО: Детекция движения теперь ВКЛЮЧЕНА.")
        else:
            print("   ОШИБКА ПРОВЕРКИ: Камера приняла запрос, но детекция осталась выключенной.")
            print("   Ответ камеры:", final_xml)

    else:
        print(f"\n ОШИБКА! Камера не приняла конфигурацию. Статус код: {put_response.status_code}")
        print("Ответ камеры:", put_response.text)


except requests.exceptions.RequestException as e:
    print(f"Ошибка соединения: {e}")