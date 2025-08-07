import logging
from fastapi import FastAPI, Request, HTTPException, Form, UploadFile
from fastapi.responses import JSONResponse
from typing import List, Optional

# Убедитесь, что импорт правильный.
from services.parse_logic_firmware_v5 import process_anpr_event_from_parts, SmartParkingService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

@app.post("/firmware_v5")
async def receive_event_endpoint(request: Request):
    """
    Эндпоинт для приема multipart/form-data событий от камер Hikvision,
    используя встроенный парсер FastAPI.
    """
    logger.info("="*20)
    logger.info(f"EVENT RECEIVED at /firmware_v5 from {request.client.host}")
    
    smart_parking_service = SmartParkingService()

    try:
        # --- НОВЫЙ, ПРОСТОЙ И НАДЕЖНЫЙ СПОСОБ ПАРСИНГА ---
        # FastAPI сам разберет multipart-запрос, если мы запросим form()
        form_data = await request.form()
        
        # Теперь form_data - это объект, похожий на словарь.
        # Давайте посмотрим, какие ключи (имена частей) в нем есть.
        logger.info(f"--- Parsed Form Data Keys ---")
        logger.info(f"Keys found: {list(form_data.keys())}")
        logger.info("---------------------------")

        # Ищем наши части. FastAPI вернет их как объекты UploadFile.
        # Ключи - это значения 'name' из Content-Disposition.
        # Например, 'MoveDetection.xml' или 'licensePlatePicture.jpg'.
        
        xml_file = None
        plate_picture_file = None
        detection_picture_file = None

        # Итерируемся по всем частям, чтобы найти нужные
        for key in form_data.keys():
            if key.lower().endswith('.xml'):
                xml_file = form_data[key]
                logger.info(f"Found XML part with key: '{key}'")
            elif key == 'licensePlatePicture.jpg':
                plate_picture_file = form_data[key]
                logger.info(f"Found licensePlatePicture part.")
            elif key == 'detectionPicture.jpg':
                detection_picture_file = form_data[key]
                logger.info(f"Found detectionPicture part.")
        
        # --- КОНЕЦ НОВОГО ПАРСИНГА ---
        
        # Читаем содержимое файлов (они типа UploadFile)
        xml_bytes = await xml_file.read() if xml_file else None
        plate_picture_bytes = await plate_picture_file.read() if plate_picture_file else None
        detection_picture_bytes = await detection_picture_file.read() if detection_picture_file else None

        processed_data = await process_anpr_event_from_parts(
            anpr_xml_bytes=xml_bytes,
            license_plate_picture_bytes=plate_picture_bytes,
            detection_picture_bytes=detection_picture_bytes
        )
        
        logger.info(f"processed_data: {processed_data}")
        
        if processed_data and processed_data.get('license_plate'):
            smart_parking_service.send_parking(
                camera_name=processed_data.get('camera'),
                main_image_path=processed_data.get('main_image_path'),
                main_image_original_name=processed_data.get('main_image_original_name'),
                license_plate=processed_data.get('license_plate'),
                license_plate_country=processed_data.get('license_plate_country'),
                color=processed_data.get('color'),
                event_id=processed_data.get('event_id')
            )
        else:
            logger.info("Событие пропущено, так как не содержит номера или произошла ошибка парсинга.")

        return JSONResponse(status_code=200, content={"status": "success"})

    except Exception as e:
        logger.exception(f"Critical error in /firmware_v5 endpoint: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": "Internal server error."})
    finally:
        logger.info("Finished /firmware_v5 endpoint processing.")
        logger.info("="*20)
        
@app.get("/")
def read_root():
    return {"Hello": "World"}