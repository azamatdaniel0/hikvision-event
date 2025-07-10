from typing import *
import requests
from requests.auth import HTTPDigestAuth
import logging
import os
from dotenv import load_dotenv
import json

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BARRIER_SERVICE")


CAMERA_ENTRY1_IP = os.getenv(
    "CAMERA_ENTRY_IP"
)
CAMERA_ENTRY2_IP = os.getenv(
    "CAMERA_ENTRY2_IP"
)
CAMERA_EXIT1_IP = os.getenv(
    "CAMERA_EXIT_IP"
)

CAMERA_EXIT2_IP = "192.168.80.173"

class BarrierService:

    def __init__(self):
        self.username = 'admin'
        self.password = 'user12345'
        # self.headers = {'Content-Type': 'application/json'}

    def management_barrier(self, camera,):

        data = {
            "SoftIO": [
            {
            "id": 1,
            "triggerType": "stop"
            }]
        }
        commands = self.commands(camera, data)
        return commands

      
    def commands(self, camera, data) -> bool:
        cameras = {
            "Exit":CAMERA_EXIT2_IP,
        }
        logger.info("Open barrier")
        CAMERA_IP = cameras[camera]
        camera_url = f"http://{CAMERA_IP}/ISAPI/System/IO/softInputs/trigger?format=json"
        digest_auth = HTTPDigestAuth(self.username, self.password)
        
        
        try:
            response = requests.put(url=camera_url,json=data,  auth=digest_auth, timeout=5)
            if response.status_code == 200:
                logger.info("Barrier opened successfully")
                return True
            else:
                logger.info(f"Failed to open barrier: {response.text}")
                return False
        except requests.exceptions.HTTPError as e:
            logger.error(f"Ошибка HTTP: {e}")
            logger.error(f"Статус код: {e.response.status_code}")
            logger.error("Ответ камеры:")
            logger.error(e.response.text)
            if e.response.status_code == 401:
                logger.error("-> Ошибка 401: Проверьте правильность имени пользователя и пароля (Digest Authentication).")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Ошибка соединения: Не удалось подключиться к камере по адресу {CAMERA_IP}.")
            logger.error(f"-> Проверьте IP-адрес, сетевое подключение и настройки файрвола.")
            logger.error(f"-> Детали ошибки: {e}")
        except requests.exceptions.Timeout as e:
            logger.error(f"Ошибка: Превышено время ожидания ответа от камеры.")
            logger.error(f"-> Детали ошибки: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Произошла ошибка при отправке запроса: {e}")

barierr = BarrierService()
barierr.management_barrier("Exit")