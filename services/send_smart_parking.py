# services/send_smart_parking.py
import requests
from config.config import SMART_PARKING_URL # Убедитесь, что SMART_PARKING_URL определен
import logging
import os
from typing import Optional
logger = logging.getLogger(__name__)

class SmartParkingService:
    def __init__(self, smart_parking_url=SMART_PARKING_URL):
        self.smart_parking_url = smart_parking_url

    def send_parking(self, camera_name: Optional[str], 
                     main_image_path: Optional[str], 
                     main_image_original_name: Optional[str], 
                     license_plate: Optional[str], 
                     license_plate_country: Optional[str], 
                     color: Optional[str], 
                     event_id: Optional[str]):
        url = f"{self.smart_parking_url}/parking/data_process/" # Убедитесь, что URL правильный

        files_to_send = None
        opened_file = None 

        if main_image_path and main_image_original_name and os.path.exists(main_image_path):
            try:
                opened_file = open(main_image_path, 'rb')
                # Сервер ожидает файл в поле с именем "photo"
                files_to_send = {'photo': (main_image_original_name, opened_file)} 
                logger.info(f"Preparing single file for upload: field='photo', filename='{main_image_original_name}', path='{main_image_path}'")
            except IOError as e:
                logger.error(f"Could not open file {main_image_path} for upload: {e}")
            except Exception as e: # Более общее исключение
                logger.error(f"Error preparing file {main_image_path}: {e}")
        else:
            if main_image_path: # Логируем, только если путь был, но файл не найден
                 logger.warning(f"Main image path '{main_image_path}' provided, but file does not exist. Sending request without image.")
            else:
                 logger.info("No main image path provided. Sending request without image.")


        data = {
            "license_plate": license_plate, 
            "license_plate_country": license_plate_country, 
            "color": color, 
            "event_id": event_id, 
            "camera": camera_name,
            "recognize": "HikVision",
        }
        # Удаляем ключи с None значениями из data, если сервер не ожидает их
        # data = {k: v for k, v in data.items() if v is not None}


        try:
            logger.info(f"Sending POST request to {url} with data: {data} and files: {'Yes' if files_to_send else 'No'}")
            response = requests.post(url=url, data=data, files=files_to_send) 

            if response.status_code == 200:
                logger.info(f"Successfully sent request to smart parking. Response: {response.text[:200]}") # Логируем начало ответа
                return True
            else:
                logger.warning(f"Failed to send request to smart parking. Status: {response.status_code}, Response: {response.text[:500]}") # Логируем начало ответа
                return response.status_code
        except requests.exceptions.RequestException as e:
            logger.error(f"Request to smart parking failed: {e}")
            return False
        finally:
            if opened_file: 
                try:
                    opened_file.close()
                    logger.info(f"Closed file: {main_image_original_name}")
                except Exception as e_close:
                    logger.error(f"Error closing file object for {main_image_original_name}: {e_close}")