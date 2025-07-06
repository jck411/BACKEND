"""
Smart home function definitions for AI function calling.

Following PROJECT_RULES.md:
- Single responsibility: Define available device functions
- Type safety with comprehensive validation
"""

from typing import Any, Dict, List


def get_smart_home_functions() -> List[Dict[str, Any]]:
    """
    Get function definitions for smart home device control.

    Returns:
        List of function definitions in OpenAI format
    """
    return [
        {
            "name": "control_light",
            "description": "Control smart lights in the home",
            "parameters": {
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "The ID of the light device (e.g., 'living_room_light', 'bedroom_light')",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["turn_on", "turn_off", "toggle", "set_brightness", "set_color"],
                        "description": "The action to perform on the light",
                    },
                    "brightness": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "Brightness level (0-100) when setting brightness",
                    },
                    "color": {
                        "type": "string",
                        "description": "Color name or hex code when setting color",
                    },
                },
                "required": ["device_id", "action"],
            },
        },
        {
            "name": "control_thermostat",
            "description": "Control the home thermostat",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["set_temperature", "set_mode", "get_status"],
                        "description": "The action to perform on the thermostat",
                    },
                    "temperature": {
                        "type": "number",
                        "minimum": 40,
                        "maximum": 90,
                        "description": "Target temperature in Fahrenheit",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["heat", "cool", "auto", "off"],
                        "description": "Thermostat mode",
                    },
                },
                "required": ["action"],
            },
        },
        {
            "name": "get_device_status",
            "description": "Get the current status of a smart home device",
            "parameters": {
                "type": "object",
                "properties": {
                    "device_id": {"type": "string", "description": "The ID of the device to check"},
                    "device_type": {
                        "type": "string",
                        "enum": ["light", "thermostat", "sensor", "switch"],
                        "description": "The type of device",
                    },
                },
                "required": ["device_id"],
            },
        },
        {
            "name": "get_weather",
            "description": "Get current weather information",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City and state/country for weather lookup",
                    }
                },
                "required": ["location"],
            },
        },
    ]


async def execute_function_call(function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a function call and return the result.

    Args:
        function_name: Name of the function to execute
        arguments: Function arguments

    Returns:
        Function execution result
    """
    # For now, simulate function execution
    # TODO: Connect to actual device control systems

    if function_name == "control_light":
        device_id = arguments.get("device_id", "unknown")
        action = arguments.get("action", "unknown")
        brightness = arguments.get("brightness")
        color = arguments.get("color")

        result = f"✅ Light '{device_id}' action '{action}' executed successfully"
        if brightness is not None:
            result += f" (brightness: {brightness}%)"
        if color:
            result += f" (color: {color})"

        return {"success": True, "message": result, "device_id": device_id, "action": action}

    elif function_name == "control_thermostat":
        action = arguments.get("action", "unknown")
        temperature = arguments.get("temperature")
        mode = arguments.get("mode")

        result = f"🌡️ Thermostat action '{action}' executed successfully"
        if temperature is not None:
            result += f" (temperature: {temperature}°F)"
        if mode:
            result += f" (mode: {mode})"

        return {
            "success": True,
            "message": result,
            "action": action,
            "current_temperature": 72,
            "target_temperature": temperature or 72,
        }

    elif function_name == "get_device_status":
        device_id = arguments.get("device_id", "unknown")
        device_type = arguments.get("device_type", "unknown")

        # Simulate device status
        if "light" in device_id.lower():
            status = {
                "device_id": device_id,
                "type": "light",
                "state": "on",
                "brightness": 75,
                "color": "warm_white",
            }
        elif "thermostat" in device_id.lower():
            status = {
                "device_id": device_id,
                "type": "thermostat",
                "current_temperature": 72,
                "target_temperature": 70,
                "mode": "heat",
            }
        else:
            status = {"device_id": device_id, "type": device_type, "state": "online"}

        return {"success": True, "device_status": status}

    elif function_name == "get_weather":
        location = arguments.get("location", "Unknown")

        return {
            "success": True,
            "location": location,
            "temperature": 75,
            "condition": "partly cloudy",
            "humidity": 65,
            "message": f"🌤️ Current weather in {location}: 75°F, partly cloudy",
        }

    else:
        return {"success": False, "error": f"Unknown function: {function_name}"}
