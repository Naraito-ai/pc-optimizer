# State Format Migration Notes (v1.x → v2.0.0)

## Overview
PC Optimizer v2.0.0 introduces **True State Management** and **Change Ownership Tracking**. 
Instead of assuming Windows defaults during restoration, v2.0.0 captures original system settings prior to modification and tracks whether each setting was changed by this application (`modified_by_optimizer: true`).

---

## State Schema Structure (`state.json`)

The state file is stored at `%APPDATA%\PCOptimizer\state.json`.

```json
{
  "version": "2.0.0",
  "last_run": "Sun 03:00 AM",
  "last_score_before": 74,
  "last_score_after": 92,
  "gaming_mode": false,
  "is_scheduled": true,
  "modified_settings": {
    "power_plan": {
      "original_scheme_guid": "381b4222-f694-41f0-9685-ff5bb260df2e",
      "modified_by_optimizer": true
    },
    "visual_effects": {
      "original_fx_setting": 0,
      "original_min_animate": "1",
      "modified_by_optimizer": true
    },
    "gamedvr": {
      "original_gamedvr_enabled": 1,
      "original_appcapture_enabled": 1,
      "modified_by_optimizer": true
    },
    "telemetry_service": {
      "original_start_type": "auto",
      "original_state": "RUNNING",
      "modified_by_optimizer": true
    },
    "scheduled_task": {
      "created_by_optimizer": true
    },
    "startup_entries": [
      {
        "hive": "HKCU",
        "key_path": "Software\\Microsoft\\Windows\\CurrentVersion\\Run",
        "disabled_key_path": "Software\\Microsoft\\Windows\\CurrentVersion\\RunDisabled",
        "value_name": "ExampleApp",
        "value_type": 1,
        "value_data": "\"C:\\Program Files\\Example\\app.exe\"",
        "timestamp": "2026-07-30T19:20:00",
        "app_version": "2.0.0",
        "modified_by_optimizer": true
      }
    ]
  }
}
```

---

## Migration Behavior
- **Backward Compatibility**: If an existing `state.json` file from v1.x is detected without `modified_settings`, `load_state()` automatically upgrades the dictionary structure in memory and saves the updated format without losing historical run data.
- **Corrupted State File Handling**: If `state.json` contains invalid or corrupted JSON data, the application falls back safely to default initial state metrics.
