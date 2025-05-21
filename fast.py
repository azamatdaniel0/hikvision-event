import fastapi
from fastapi import FastAPI, Request, File, UploadFile, HTTPException
from typing import Optional
from fastapi.responses import JSONResponse
import logging

from services.parse_logic import process_anpr_event 
from services.send_smart_parking import SmartParkingService
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()



@app.post("/test")
async def receive_event_endpoint(  
    request: Request, 
    anpr_xml: Optional[UploadFile] = File(None, alias="anpr.xml"),  
    license_plate_picture: Optional[UploadFile] = File(None, alias="licensePlatePicture.jpg"),
    detection_picture: Optional[UploadFile] = File(None, alias="detectionPicture.jpg")
    ):
    send_smart_parking = SmartParkingService()
    logger.info("="*20)
    logger.info(f"EVENT RECEIVED at /test from {request.client.host}")

    try:
        processed_data = await process_anpr_event(
            anpr_xml_file=anpr_xml,
            license_plate_picture_file=license_plate_picture,
            detection_picture_file=detection_picture
        )
        
        # Используем .get() с значениями по умолчанию для безопасности
        camera = processed_data.get('camera', 'Unknown')
        license_plate = processed_data.get('license_plate')
        event_id = processed_data.get('event_id')
        main_image_path = processed_data.get('main_image_path')
        main_image_original_name = processed_data.get('main_image_original_name')
        color = processed_data.get('color', 'default') 
        license_plate_country = processed_data.get('license_plate_country', 'default') 
        
        
        send_server_result = send_smart_parking.send_parking( 
            camera_name=camera, 
            main_image_path=main_image_path, 
            main_image_original_name=main_image_original_name, 
            license_plate=license_plate, 
            license_plate_country=license_plate_country, 
            color=color, 
            event_id=event_id
        )
        if send_server_result:
            logger.info("Success send request to smart parking 200 OK")
            logger.info(f"Processed data: {processed_data}")
        
        if processed_data.get("parsing_errors"):
            return JSONResponse(
                status_code=200,  
                content={
                    "status": "partial_success" if processed_data.get("plate_number") else "failure", # или другой статус
                    "message": "Event received, but some data could not be parsed.",
                    "data": processed_data,
                    "errors": processed_data["parsing_errors"]
                }
            )
        
        return JSONResponse(
            content={
                "status": "success",
                "message": "Event received and processed successfully",
                "data": processed_data
            }
        )

    except HTTPException as http_ex: 
        raise http_ex
    except Exception as e:
        logger.exception(f"Critical error in /test endpoint: {e}")
         
        return JSONResponse(status_code=500, content={"status": "error", "message": "Internal server error during event processing."})
    finally:
        logger.info("Finished /test endpoint processing.")
        logger.info("="*20)


@app.get("/")
def read_root():
    return {"Hello": "World"}

# Ваш код для настройки камеры (put_config) можно оставить здесь или вынести в отдельный скрипт
# ... 
# def put_config(): ...
# if __name__ == "__main__" and some_condition_to_run_put_config:
#    print(put_config())