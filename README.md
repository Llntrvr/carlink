# CarLink (CL7) for Home Assistant

> [!WARNING]
> **Unofficial.** This is not made, supported or endorsed by VOXX, CarLink or Automobility.
>
> **100% vibe coded.** It was built with an AI assistant by reading the CL7 app and testing against one account
> and one car. It hasn't been reviewed or tested beyond that.
>
> **Remote start only.** It can start and stop the engine. It does **not** lock or unlock the car doors, and
> it has no way to: the only commands it can send are remote start and stop.
>
> **No guarantee it keeps working.** It relies on a private service that can change at any time, so we can't
> promise it will still work next week. Use it at your own risk.

Home Assistant integration for **VOXX CarLink** cellular remote-start modules (ASCL7, the **CL7** app).
It remote starts and stops the car and shows its status.

It talks to the same cloud as the CL7 app: AWS Cognito login (us-east-1), then `https://api.mybrandedapp.com`.
Worked out from the CL7 Android app (v1.4.0) and the account's own API answers; VOXX publishes no API, so it may
break if they change their service.

## Install

1. Copy `custom_components/carlink` to `/config/custom_components/carlink` on Home Assistant and restart.
2. **Settings → Devices & services → Add integration → CarLink (CL7)**, then sign in with your CL7 email and password.

## What you get (one device per vehicle)

| Entity | What it does |
|---|---|
| `lock.<car>_remote_start` | **Unlock = remote start**, **lock = stop**. Unlocked = engine running. A lock, so starting is a deliberate action (Google Assistant asks for its PIN to unlock). |
| `binary_sensor.<car>_engine` / `_doors` / `_trunk` / `_hood` | From the module's last report |
| `binary_sensor.<car>_module_online` | Diagnostic |
| `sensor.<car>_battery` | Volts |
| `sensor.<car>_cabin_temperature` | |
| `sensor.<car>_remote_start_time_left` | Seconds, 0 when off |
| `sensor.<car>_last_start_event` | e.g. "Remote start success" |
| `sensor.<car>_signal`, `sensor.<car>_last_report` | Diagnostic |
| `device_tracker.<car>_location` | GPS from the module's reports |

## Safety

- Only two commands can be sent: `carCommand` **3 (remote start)** and **4 (stop)**. `api.send_command` refuses
  anything else, so lock (0), unlock (1) and trunk can't be sent even by mistake.
- Status comes from the module's last stored report (`GetLastVehicleStatus`): reading it doesn't wake the car.
  Polled every 3 minutes, every 45 seconds while the engine runs.
- The cloud's lock status (`Status_Lock`) is not shown: it didn't match the car.

## API notes

| Call | Use |
|---|---|
| `POST cognito-idp.us-east-1.amazonaws.com` `InitiateAuth` | `USER_PASSWORD_AUTH` / `REFRESH_TOKEN_AUTH`, client `3t704g14i0l52mfkt77ldaoshp`; the API takes the **IdToken** |
| `GET CarstarterService/GetAllVehicles/MyCar2?lang=en` | Vehicles (`Id` is the vehicle GUID) |
| `GET CarstarterService/GetLastVehicleStatus/{Id}` | Last status: `Status_Engine`, `StartEvent`, `Runtime_1s`, `BatteryVoltage` (mV), `InteriorTemperature` (°C), GPS |
| `POST CarstarterService/SendCarCommand` | Body `{"vehicleId": "<Id>", "carCommand": 3 or 4}` |
| `GET CarstarterService/GetVehicleActivities/{Id}?pageNumber=1&pageSize=20` | Command history (`CarAction` entries carry the command number) |
