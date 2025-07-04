import requests
import xml.etree.ElementTree as ET
import time
import re
from requests.auth import HTTPDigestAuth

# --- Настройки подключения ---
CAMERA_IP = "192.168.80.171"
USERNAME = "admin" # Обычно 'admin'
PASSWORD = "user12345"
# ---------------------------

# URL для получения потока событий
event_stream_url = f"http://{CAMERA_IP}/ISAPI/Event/notification/alertStream"

print(f"Подключение к камере: {CAMERA_IP}...")
print("Ожидание событий (детекция транспорта)... Нажмите Ctrl+C для выхода.")

session = requests.Session()
session.auth = HTTPDigestAuth(USERNAME, PASSWORD)
namespace = {'isapi': 'http://www.hikvision.com/ver20/XMLSchema'}  

def find_tag(element, tag_name):
    """Вспомогательная функция для поиска тега с учетом namespace."""
    # Пытаемся найти с namespace
    namespaced_tag = f".//isapi:{tag_name}"
    found = element.find(namespaced_tag, namespace)
    if found is not None:
        return found
    plain_tag = f".//{tag_name}"
    found = element.find(plain_tag)
    return found

def process_event_xml(xml_data):
    """Обрабатывает XML одного события."""
    try:
        xml_start = xml_data.find('<?xml')
        if xml_start == -1:
            xml_start = xml_data.find('<EventNotificationAlert')
        if xml_start == -1:
            return

        clean_xml = xml_data[xml_start:]
        root = ET.fromstring(clean_xml)

        eventType_elem = find_tag(root, 'eventType')
        eventState_elem = find_tag(root, 'eventState')
        channelID_elem = find_tag(root, 'channelID') # или 'dynChannelID' для NVR
        dateTime_elem = find_tag(root, 'dateTime')
        eventDescription_elem = find_tag(root, 'eventDescription')

        event_type = eventType_elem.text if eventType_elem is not None else "N/A"
        event_state = eventState_elem.text if eventState_elem is not None else "N/A"
        channel_id = channelID_elem.text if channelID_elem is not None else find_tag(root, 'dynChannelID').text if find_tag(root, 'dynChannelID') is not None else "N/A"
        date_time = dateTime_elem.text if dateTime_elem is not None else "N/A"
        description = eventDescription_elem.text if eventDescription_elem is not None else "N/A"

        target_event_types = ["vehicledetection", "ruleenginedetection", "fielddetection", "linedetection"] # Примеры!

        is_vehicle_event = False
        for target_type in target_event_types:
             if target_type in event_type.lower():
                 if "vehicle" in description.lower():
                     is_vehicle_event = True
                     break
                 if target_type == "vehicledetection":
                      is_vehicle_event = True
                      break


        if is_vehicle_event and event_state == 'active': # Реагируем на начало события
            print("-" * 30)
            print(f"Обнаружено ТС!")
            print(f"  Время: {date_time}")
            print(f"  Канал: {channel_id}")
            print(f"  Тип события: {event_type}")
            print(f"  Состояние: {event_state}")
            print(f"  Описание: {description}")
            target_rect_elem = find_tag(root, 'TargetRect')
            if target_rect_elem is not None:
                 print(f"  Область: x={target_rect_elem.get('x')}, y={target_rect_elem.get('y')}, "
                       f"width={target_rect_elem.get('width')}, height={target_rect_elem.get('height')}")
            print("-" * 30)

    except ET.ParseError as e:
        print(f"Ошибка парсинга XML: {e}")
        print(f"Проблемный XML (начало): {xml_data[:200]}...") # Отладка
    except Exception as e:
        print(f"Неизвестная ошибка при обработке события: {e}")
        print(f"Данные (начало): {xml_data[:200]}...") # Отладка


def listen_for_events():
    """Основной цикл прослушивания событий."""
    while True:
        try:
            response = session.get(event_stream_url, stream=True, timeout=60) # Таймаут long polling
            response.raise_for_status() # Проверка на HTTP ошибки (4xx, 5xx)

            boundary = None
            content_type_header = response.headers.get('Content-Type', '')

            match = re.search(r'boundary="?([^"]+)"?', content_type_header)
            if match:
                boundary = match.group(1)

            full_content = b''
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    full_content += chunk
                    if not boundary:
                         # Простой случай - один XML на ответ
                         try:
                            decoded_chunk = full_content.decode('utf-8', errors='ignore')
                            if decoded_chunk.strip().endswith('</EventNotificationAlert>'):
                                 # print(f"Обработка единичного XML...") # Отладка
                                 process_event_xml(decoded_chunk)
                                 full_content = b'' # Сбрасываем буфер
                         except Exception as e:
                             print(f"Ошибка при обработке единичного ответа: {e}")
                             full_content = b'' # Сброс при ошибке

            # Обработка multipart ответа после получения всего контента
            if boundary:
                #print("Обработка multipart ответа...") # Отладка
                try:
                    body = full_content.decode('utf-8', errors='ignore')
                    parts = body.split(f'--{boundary}')
                    #print(f"Найдено частей: {len(parts)}") # Отладка
                    for part in parts:
                        if part.strip() and part.strip() != '--': # Пропускаем пустые части и закрывающий boundary
                            # Ищем начало XML внутри части
                             process_event_xml(part)
                except Exception as e:
                    print(f"Ошибка при разборе multipart: {e}")
                    print(f"Контент (начало): {full_content[:500]}") # Отладка


        except requests.exceptions.ConnectionError as e:
            print(f"Ошибка соединения: {e}. Повторная попытка через 10 секунд...")
            time.sleep(10)
        except requests.exceptions.Timeout:
            # Это нормальное поведение для long polling, если событий не было
            # print("Таймаут ожидания события, переподключение...")
            continue
        except requests.exceptions.HTTPError as e:
            print(f"HTTP ошибка: {e.response.status_code} {e.response.reason}")
            if e.response.status_code == 401:
                print("Ошибка аутентификации (Unauthorized). Проверьте логин и пароль.")
            elif e.response.status_code == 404:
                 print("Ошибка 404 (Not Found). Неверный URL или ISAPI события не поддерживаются/отключены.")
            else:
                print(f"Ответ сервера: {e.response.text}")
            print("Ожидание 15 секунд перед повторной попыткой...")
            time.sleep(15)
        except requests.exceptions.RequestException as e:
            print(f"Общая ошибка запроса: {e}. Повторная попытка через 10 секунд...")
            time.sleep(10)
        except KeyboardInterrupt:
            print("\nВыход из программы.")
            break
        except Exception as e:
            print(f"Непредвиденная ошибка в основном цикле: {e}")
            time.sleep(5)


if __name__ == "__main__":
    listen_for_events()