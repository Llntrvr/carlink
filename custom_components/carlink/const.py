"""Constants for the unofficial CarLink (VOXX CL7 / Automobility) integration."""
from datetime import timedelta

DOMAIN = "carlink"

# Found in the CL7 Android app (app.com.automobility.mycar.control2.cl7, v1.4.0) and confirmed against the API.
COGNITO_URL = "https://cognito-idp.us-east-1.amazonaws.com/"
COGNITO_CLIENT_ID = "3t704g14i0l52mfkt77ldaoshp"
API_BASE = "https://api.mybrandedapp.com/CarstarterService/"
APP_BRAND = "MyCar2"

# The only commands this integration can send (confirmed from the account's command history:
# the CL7 app's Remote Start logs carCommand 3, its Stop logs 4). Lock/unlock/trunk are deliberately absent.
CMD_START = 3
CMD_STOP = 4
ALLOWED_COMMANDS = frozenset({CMD_START, CMD_STOP})

# Stored status is read from the cloud (it doesn't wake the car): quicker while the engine runs.
SCAN_INTERVAL = timedelta(minutes=3)
SCAN_INTERVAL_RUNNING = timedelta(seconds=45)
