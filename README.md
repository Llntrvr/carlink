# CarLink (CL7) for Home Assistant

> [!WARNING]
> **Unofficial.** This is not made, supported or endorsed by VOXX, CarLink or Automobility.
>
> **100% vibe coded.** It was built with an AI assistant by reading the CL7 app and testing against one account
> and one car. It hasn't been reviewed or tested beyond that.
>
> **It can unlock your car.** Besides remote start and stop it can lock and unlock the doors, open the trunk and run the
> accessories set up in the CL7 app. Anyone who can use your Home Assistant can do the same, so keep it secured.
>
> **No guarantee it keeps working.** It relies on a private service that can change at any time, so we can't
> promise it will still work next week. Use it at your own risk.

Home Assistant integration for **VOXX CarLink** cellular remote-start modules (ASCL7, the **CL7** app).
It remote starts and stops the car, locks and unlocks the doors, opens the trunk, runs the accessories set up in the app,
and shows the car's status.

It talks to the same cloud as the CL7 app: AWS Cognito login (us-east-1), then `https://api.mybrandedapp.com`.
Worked out from the CL7 Android app (v1.4.0) and the account's own API answers; VOXX publishes no API, so it may
break if they change their service.

## Install

### With HACS

1. **HACS → ⋮ (top right) → Custom repositories**: add `https://github.com/Llntrvr/carlink`, type **Integration**.
2. Find **CarLink (CL7)** in HACS, **Download**, then restart Home Assistant.
3. **Settings → Devices & services → Add integration → CarLink (CL7)**, then sign in with your CL7 email and password.

### By hand

1. Copy `custom_components/carlink` to `/config/custom_components/carlink` on Home Assistant and restart.
2. **Settings → Devices & services → Add integration → CarLink (CL7)**, then sign in with your CL7 email and password.

## What you get (one device per vehicle)

| Entity | What it does |
|---|---|
| `lock.<car>_remote_start` | **Unlock = remote start**, **lock = stop**. Unlocked = engine running. A lock, so starting is a deliberate action (Google Assistant asks for its PIN to unlock). |
| `lock.<car>_doors` | Locks and unlocks the doors. The state is the last command sent from Home Assistant (the cloud's lock reading didn't match the car), so a lock from the app or key fob isn't seen. |
| `button.<car>_open_trunk` | Trunk / hatch release, like the app's trunk button. |
| `button.<car>_<accessory>` | One per accessory set up in the CL7 app (Settings → Auxiliaries), named as in the app, e.g. `button.<car>_windows_roll_down`. It only sends the command: it does nothing if the module isn't wired for it. Disable the ones you don't use. |
| `binary_sensor.<car>_engine` / `_doors` / `_trunk` / `_hood` | From the module's last report |
| `binary_sensor.<car>_module_online` | Diagnostic |
| `sensor.<car>_battery` | Volts |
| `sensor.<car>_cabin_temperature` | |
| `sensor.<car>_remote_start_time_left` | Seconds, 0 when off |
| `sensor.<car>_last_start_event` | e.g. "Remote start success" |
| `sensor.<car>_signal`, `sensor.<car>_last_report` | Diagnostic |
| `device_tracker.<car>_location` | GPS from the module's reports |

## Safety

- `api.send_command` only sends **0 (lock)**, **1 (unlock)**, **2 (trunk)**, **3 (remote start)**, **4 (stop)** and the
  accessory commands listed for that car in the app. Anything else is refused.
- Both locks are lock entities, so Google Assistant asks for its PIN before unlocking or starting, and dashboards
  confirm. Don't expose `lock.<car>_doors` to voice assistants without a PIN.
- Status comes from the module's last stored report (`GetLastVehicleStatus`): reading it doesn't wake the car.
  Polled every 3 minutes, every 45 seconds while the engine runs.
- The cloud's lock status (`Status_Lock`) is not shown: it didn't match the car.

## API notes

| Call | Use |
|---|---|
| `POST cognito-idp.us-east-1.amazonaws.com` `InitiateAuth` | `USER_PASSWORD_AUTH` / `REFRESH_TOKEN_AUTH`, client `3t704g14i0l52mfkt77ldaoshp`; the API takes the **IdToken** |
| `GET CarstarterService/GetAllVehicles/MyCar2?lang=en` | Vehicles (`Id` is the vehicle GUID; `Aux` lists the app's accessories with their `CarCommand`) |
| `GET CarstarterService/GetLastVehicleStatus/{Id}` | Last status: `Status_Engine`, `StartEvent`, `Runtime_1s`, `BatteryVoltage` (mV), `InteriorTemperature` (°C), GPS |
| `POST CarstarterService/SendCarCommand` | Body `{"vehicleId": "<Id>", "carCommand": n}`: 0 lock, 1 unlock, 2 trunk, 3 start, 4 stop, accessories from `Aux` |
| `GET CarstarterService/GetVehicleActivities/{Id}?pageNumber=1&pageSize=20` | Command history (`CarAction` entries carry the command number) |
