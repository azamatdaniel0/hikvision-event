# services/parse_logic_firmware_v5.py

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
import uuid
import time
import requests

# --- НАСТРОЙКИ ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Укажите путь, куда сервис будет сохранять полученные изображения
IMAGE_STORAGE_PATH = Path("./event_images")
IMAGE_STORAGE_PATH.mkdir(exist_ok=True) # Создаем папку, если она не существует

# Адрес вашего основного Django-бэкенда SmartParking
SMART_PARKING_API_URL = "http://192.168.80.112:8833/parking/data_process/"

class SmartParkingService:
    """
    Отвечает за отправку обработанных данных на основной сервер SmartParking.
    """
    def send_parking(self, camera_name, main_image_path, main_image_original_name, license_plate, license_plate_country, color, event_id):
        logger.info(f"Sending POST request to {SMART_PARKING_API_URL} with data: {{'license_plate': '{license_plate}', 'event_id': '{event_id}', 'camera': '{camera_name}'}} and files: {'Yes' if main_image_path else 'No'}")

        data = {
            'license_plate': license_plate,
            'license_plate_country': license_plate_country,
            'color': color,
            'event_id': event_id,
            'camera': camera_name,
            'recognize': 'HikVision'
        }

        files = None
        if main_image_path and Path(main_image_path).exists():
            try:
                files = {'photo': (main_image_original_name, open(main_image_path, 'rb'), 'image/jpeg')}
            except IOError as e:
                logger.error(f"Could not open image file {main_image_path}: {e}")
                main_image_path = None 

        try:
            response = requests.post(SMART_PARKING_API_URL, data=data, files=files)
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully sent data to SmartParking. Response: {response.json()}")
                return True
            else:
                logger.warning(f"Failed to send request to SmartParking. Status: {response.status_code}, Response: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to SmartParking service: {e}")
            return False
        finally:
            if files:
                files['photo'][1].close()

async def process_anpr_event_from_parts(anpr_xml_bytes, license_plate_picture_bytes, detection_picture_bytes):
    """
    Главная функция, которая парсит XML, сохраняет изображение и возвращает структурированные данные.
    """
    parsing_errors = []
    
    # --- Шаг 1: Парсинг XML (без изменений) ---
    if not anpr_xml_bytes:
        logger.warning("XML data part is missing.")
        parsing_errors.append("XML data part is missing.")
        return {'parsing_errors': parsing_errors}
    
    license_plate, event_id, camera, color, country, event_type = None, None, 'Unknown', 'default', 'default', 'Unknown'
    
    try:
        xml_content = anpr_xml_bytes.decode('utf-8').replace('xmlns="http://www.hikvision.com/ver20/XMLSchema"', '').replace('xmlns="http://www.std-cgi.com/ver20/XMLSchema"', '')
        root = ET.fromstring(xml_content)
        
        event_type_element = root.find('.//eventType')
        event_type = event_type_element.text if event_type_element is not None else "Unknown"
        logger.info(f"Обнаружен тип события: {event_type}")

        channel_name_element = root.find('.//channelName')
        device_id_element = root.find('.//deviceId')
        camera = "Exit"

        short_uuid = str(uuid.uuid4()).split('-')[0]
        timestamp = str(int(time.time() * 1000))[-8:]
        event_id = f"{short_uuid}-{timestamp}"

        if event_type == 'ANPR':
            plate_element = root.find('.//licensePlate')
            color_element = root.find('.//color')
            country_element = root.find('.//country')

            license_plate = plate_element.text.strip() if plate_element is not None and plate_element.text else None
            color = color_element.text if color_element is not None and color_element.text != 'unknown' else 'default'
            country = country_element.text if country_element is not None and country_element.text else 'default'
        else:
            license_plate = None
            if event_type == 'VMD':
                logger.info("Это событие детекции движения, номер не распознается.")
        
        if event_type == 'ANPR' and not license_plate:
            parsing_errors.append("ANPR event received, but could not find 'licensePlate' in XML.")
            
    except Exception as e:
        logger.exception(f"An unexpected error occurred during XML processing: {e}")
        parsing_errors.append(f"Unexpected error during XML processing: {e}")

    # --- Шаг 2: Сохранение изображения (ЗДЕСЬ ИЗМЕНЕНИЯ) ---
    main_image_path = None
    main_image_original_name = None
    
    # --- ИЗМЕНЕНИЕ 1: МЕНЯЕМ ПРИОРИТЕТ ---
    # Теперь мы сначала ищем полное фото (`detectionPicture`), и только если его нет,
    # берем обрезанное (`licensePlatePicture`).
    image_to_save_bytes = detection_picture_bytes or license_plate_picture_bytes
    # ----------------------------------------

    if image_to_save_bytes:
        try:
            file_name = f"{event_id}.jpg"
            save_path = IMAGE_STORAGE_PATH / file_name
            
            with open(save_path, "wb") as f:
                f.write(image_to_save_bytes)

            main_image_path = str(save_path)
            
            # --- ИЗМЕНЕНИЕ 2: УКАЗЫВАЕМ ПРАВИЛЬНОЕ ИМЯ ---
            main_image_original_name = "detectionPicture.jpg" if detection_picture_bytes else "licensePlatePicture.jpg"
            # ---------------------------------------------

            logger.info(f"Image saved successfully to: {main_image_path} (type: {main_image_original_name})")
        except Exception as e:
            logger.exception(f"Failed to save image: {e}")
            parsing_errors.append("Failed to save image.")
    else:
        logger.warning("No image data found in the request.")
        parsing_errors.append("No image data found.")

    # --- Шаг 3: Возвращаем результат (без изменений) ---
    return {
        'license_plate': license_plate,
        'event_id': event_id,
        'camera': camera,
        'color': color,
        'license_plate_country': country,
        'main_image_path': main_image_path,
        'main_image_original_name': main_image_original_name,
        'parsing_errors': parsing_errors if parsing_errors else None
    }