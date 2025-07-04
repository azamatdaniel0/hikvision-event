import requests
import xml.etree.ElementTree as ET
import time
import re
from requests.auth import HTTPDigestAuth

CAMERA_IP = "192.168.80.173"
USERNAME = "admin"  
PASSWORD = "user12345"

HIKVISION_EVENT_STREAM_URL = f"http://{CAMERA_IP}/ISAPI/Event/notification/alertStream"
IP = '192.168.80.100'
IP = '192.168.80.112'
# IP = '192.168.80.35'


PORT = '8786'
ID = '1'

def put_config():
    data = f""""
    <?xml version="1.0" encoding="UTF-8"?>
    <HttpHostNotification version="2.0"
    xmlns="http://www.isapi.org/ver20/XMLSchema">
    <id>{ID}</id>
    <url>/test</url>
    <addressingFormatType>ipaddress</addressingFormatType>
    <ipAddress>{IP}</ipAddress>
    <portNo>{PORT}</portNo>
    </HttpHostNotification>
    """
    
    event_stream_url = f"{HIKVISION_EVENT_STREAM_URL}"
    
    try:
        response = requests.put(
            url=event_stream_url,
            auth=HTTPDigestAuth(USERNAME, PASSWORD),
            data=data,
            headers={'Content-Type': 'application/xml'}, # Good practice to specify content type
            timeout=15 # Increased timeout slightly
        )
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        print(f"Configuration successful! Status Code: {response.status_code}")
        print("Response Text:")
        print(response.text) # Check the camera's response XML for status
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error sending configuration: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Status Code: {e.response.status_code}")
            print(f"Response Body: {e.response.text}")
        return None
print(put_config()) 
    
     