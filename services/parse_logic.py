# services/parse_logic.py
import xml.etree.ElementTree as ET
import logging
import os
import time
from fastapi import UploadFile
from typing import Optional, Tuple # Добавили Tuple для аннотации
from config.config import CAMERA_171, CAMERA_172

logger = logging.getLogger(__name__)

async def process_anpr_event(
    anpr_xml_file: Optional[UploadFile],
    license_plate_picture_file: Optional[UploadFile],
    detection_picture_file: Optional[UploadFile]
) -> dict:
    """
    Обрабатывает событие ANPR, парсит XML, сохраняет ОДНО основное изображение.
    Возвращает словарь с извлеченными данными, включая путь к основному изображению.
    """
    # Инициализация переменных
    camera = "Unknown"  # Значение по умолчанию для camera
    ipaddres_str = None # Для хранения текстового IP
    plate_number = None
    event_type = None
    event_time = None
    channel_id = None
    xml_content_string = None
    
    main_image_path: Optional[str] = None
    main_image_original_name: Optional[str] = None
    
    parsing_errors = []

    # Парсинг XML
    if not anpr_xml_file:
        logger.warning("'anpr.xml' part is missing, proceeding without XML data.")
    else:
        try:
            xml_content_bytes = await anpr_xml_file.read()
            try:
                xml_content_string = xml_content_bytes.decode('utf-8')
                logger.info(f"Received ANPR XML Content:\n{xml_content_string}")
                
                root = ET.fromstring(xml_content_string)
                namespaces = {'isapi': 'http://www.isapi.org/ver20/XMLSchema'}

                # Поиск номера автомобиля
                plate_paths_to_try = [
                    './/isapi:ANPR/isapi:licensePlate', './/isapi:LPR/isapi:licensePlate',
                    './/isapi:ANPR/isapi:plateNumber', './/isapi:LPR/isapi:plateNumber'
                ]
                for path in plate_paths_to_try:
                    plate_element = root.find(path, namespaces)
                    if plate_element is not None and plate_element.text:
                        plate_number = plate_element.text.strip()
                        logger.info(f"Found Plate Number using path '{path}': {plate_number}")
                        break
                if plate_number is None:
                    logger.warning("License plate element not found in the received XML.")
                    parsing_errors.append("License plate not found in XML")

                # Поиск типа события
                event_type_element = root.find('.//isapi:eventType', namespaces)
                if event_type_element is not None and event_type_element.text:
                    event_type = event_type_element.text.strip()
                
                # Поиск IP-адреса (проверьте правильность тега: ipAddress или ipAddres)
                ip_element = root.find('.//isapi:ipAddress', namespaces) # Предполагаем 'ipAddress'
                if ip_element is None: # Если 'ipAddress' не найден, пробуем 'ipAddres'
                    ip_element = root.find('.//isapi:ipAddres', namespaces)
                
                if ip_element is not None and ip_element.text:
                    ipaddres_str = ip_element.text.strip() # Сохраняем как строку
                
                # Поиск времени события
                event_time_element = root.find('.//isapi:dateTime', namespaces)
                if event_time_element is not None and event_time_element.text:
                    event_time = event_time_element.text.strip()
                
                # Поиск ID канала
                channel_id_element = root.find('.//isapi:channelID', namespaces)
                if channel_id_element is not None and channel_id_element.text:
                    channel_id = channel_id_element.text.strip()
                
                logger.info(f"Extracted IP Address: {ipaddres_str}")
                logger.info(f"Extracted Event Type: {event_type}")
                logger.info(f"Extracted Event Time: {event_time}")
                logger.info(f"Extracted Channel ID: {channel_id}")
                logger.info(f"Extracted Plate Number: {plate_number}")

            except ET.ParseError as xml_err:
                logger.error(f"Failed to parse ANPR XML: {xml_err}")
                logger.error(f"XML Content that failed to parse:\n{xml_content_string or xml_content_bytes[:500]}") # Покажем начало, если строка не None
                parsing_errors.append(f"XML Parse Error: {xml_err}")
            except Exception as parse_ex:
                logger.exception(f"Error parsing ANPR XML content: {parse_ex}")
                parsing_errors.append(f"XML Parsing Exception: {parse_ex}")
        except Exception as e:
            logger.exception(f"An error occurred processing the 'anpr.xml' part: {e}")
            parsing_errors.append(f"Error reading anpr.xml: {e}")
        finally:
            if anpr_xml_file:
                try:
                    await anpr_xml_file.close()
                except Exception as e_close:
                    logger.error(f"Error closing anpr_xml_file: {e_close}")

    # Сохранение основного изображения
    save_path = "received_images"
    if not os.path.exists(save_path):
        os.makedirs(save_path)
        logger.info(f"Created directory: {save_path}")

    async def save_single_image(upload_file: Optional[UploadFile], file_type_prefix: str) -> Optional[Tuple[str, str]]:
        if upload_file:
            logger.info(f"Received main image candidate ({file_type_prefix}): {upload_file.filename}, Content-Type: {upload_file.content_type}")
            try:
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                unique_id = str(time.time_ns())
                # Используем file_type_prefix для более осмысленного имени, если original_filename_base пуст или не очень хорош
                original_filename_base, original_filename_ext = os.path.splitext(upload_file.filename)
                safe_filename_base = "".join(c if c.isalnum() or c in ('_') else '_' for c in original_filename_base)
                if not safe_filename_base: # Если имя файла пустое или состоит из недопустимых символов
                    safe_filename_base = file_type_prefix

                safe_ext = original_filename_ext.lower() if original_filename_ext and original_filename_ext.lower() in ['.jpg', '.jpeg', '.png'] else '.jpg'
                
                file_location = os.path.join(save_path, f"{timestamp}_{unique_id}_{safe_filename_base}{safe_ext}")
                
                with open(file_location, "wb") as buffer:
                    content = await upload_file.read()
                    buffer.write(content)
                logger.info(f"Saved main image ({file_type_prefix}) to: {file_location}")
                return file_location, upload_file.filename
            except Exception as e_save:
                logger.error(f"Error saving {file_type_prefix} ({upload_file.filename}): {e_save}")
                parsing_errors.append(f"Error saving {file_type_prefix}: {e_save}")
                return None, None
            finally:
                try:
                    await upload_file.close() # Закрываем файл после чтения
                except Exception as e_close:
                    logger.error(f"Error closing {file_type_prefix} file: {e_close}")
        return None, None

    # Пытаемся сохранить detection_picture как основное
    if detection_picture_file:
        path_info = await save_single_image(detection_picture_file, "detection_image")
        if path_info:
            main_image_path, main_image_original_name = path_info
    
    # Если detection_picture не было, или не удалось сохранить, пробуем license_plate_picture
    if not main_image_path and license_plate_picture_file:
        logger.info("Detection picture not available or failed to save, trying license plate picture as main image.")
        path_info = await save_single_image(license_plate_picture_file, "license_plate_image")
        if path_info:
            main_image_path, main_image_original_name = path_info

    if not main_image_path:
        logger.warning("No image could be saved as the main image.")
        parsing_errors.append("No main image saved")
        
    logger.info("Event processing logic finished.")

    # Определение имени камеры
    if ipaddres_str == CAMERA_171: # Сравниваем строку с строкой
        camera = "Entry"
    elif ipaddres_str == CAMERA_172:
        camera = "Entry2"
    # else: camera остается "Unknown" (установлено при инициализации)

    return {
        "license_plate": plate_number,
        "event_id": event_type,
        "main_image_path": main_image_path, # Путь к одному основному изображению
        "main_image_original_name": main_image_original_name, # Его оригинальное имя
        "ipaddres": ipaddres_str, # Возвращаем текстовый IP
        "camera": camera,
        "color": "default",
        "license_plate_country": "default",
        "parsing_errors": parsing_errors # Также возвращаем ошибки, если они были
    }