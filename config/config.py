import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()



SMART_PARKING_URL = os.getenv(
    "SMART_PARKING_URL",
    "http://192.168.80.112:8833",
)


CAMERA_171 = os.getenv(
    "CAMERA_171",
)
CAMERA_172 = os.getenv(
    "CAMERA_172",
)