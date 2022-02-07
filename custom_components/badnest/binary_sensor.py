import logging
from datetime import datetime
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant import core
from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import (
    DOMAIN,
    SENSOR_CO_STATUS,
    SENSOR_SMOKE_STATUS,
    BINARY_SENSOR_MOTION,
    BINARY_SENSOR_LINE_POWER,
    BINARY_SENSOR_OCCUPANCY,
)

_LOGGER = logging.getLogger(__name__)

PROTECT_BINARY_SENSOR_TYPES = [
    SENSOR_CO_STATUS,
    SENSOR_SMOKE_STATUS,
    BINARY_SENSOR_MOTION,
    BINARY_SENSOR_LINE_POWER,
    BINARY_SENSOR_OCCUPANCY,
    "health",
    "device"
]

friendly_names = {
    SENSOR_CO_STATUS: "CO Status",
    SENSOR_SMOKE_STATUS: "Smoke Status",
    BINARY_SENSOR_MOTION: "Motion",
    BINARY_SENSOR_LINE_POWER: "Line Power",
    BINARY_SENSOR_OCCUPANCY: "Occupancy",
    "health": "Health",
    "device": "Device"
}


async def async_setup_platform(hass: core.HomeAssistant, config, async_add_entities, discovery_info=None):
    """Set up the Protect device"""
    api = hass.data[DOMAIN]['api']

    protect_sensors = []
    _LOGGER.info("Adding protect sensors")
    for sensor in api['protects']:
        _LOGGER.info(f"Adding nest protect binary sensor uuid: {sensor}")
        for sensor_type in PROTECT_BINARY_SENSOR_TYPES:
            protect_sensors.append(NestProtectBinarySensor(sensor, sensor_type, api))

    async_add_entities(protect_sensors)


class NestProtectBinarySensor(BinarySensorEntity):
    """Implementation of the Nest Protect sensor."""

    def __init__(self, device_id, sensor_type, api):
        """Initialize the sensor."""
        self._name = "Nest Protect Sensor"
        self.device_id = device_id
        self._sensor_type = sensor_type
        self.device = api
        if sensor_type == 'health':
            self._attr_extra_state_attributes = {
                "component_wifi_test_passed": None,
                "component_co_test_passed": None,
                "component_smoke_test_passed": None,
                "component_speaker_test_passed": None,
                "component_led_test_passed": None,
                "last_audio_self_test_end_utc_secs": None,
            }
        if sensor_type == 'device':
            self._attr_extra_state_attributes = {
                "manufactured_on": None,
                "replace_by": None,
                "serial_number": None,
                "power_source": None,
            }

    @property
    def name(self) -> str:
        """Return friendly name of the sensor."""
        return self.device.device_data[self.device_id]['name'] + " " + friendly_names[self._sensor_type]

    @property
    def unique_id(self) -> str:
        """Return the unique id of the sensor."""
        return self.device.device_data[self.device_id]['name'] + \
               f' {self._sensor_type}'

    @property
    def is_on(self):
        """Return true if sensor is on."""

        if self._sensor_type == SENSOR_CO_STATUS:
            return self.device.device_data[self.device_id][self._sensor_type] > 0
        if self._sensor_type == SENSOR_SMOKE_STATUS:
            return self.device.device_data[self.device_id][self._sensor_type] > 0
        if self._sensor_type == BINARY_SENSOR_MOTION:
            return not self.device.device_data[self.device_id][self._sensor_type]
        if self._sensor_type == BINARY_SENSOR_LINE_POWER:
            return self.device.device_data[self.device_id][self._sensor_type]
        if self._sensor_type == BINARY_SENSOR_OCCUPANCY:
            return not self.device.device_data[self.device_id][self._sensor_type]
        if self._sensor_type == 'device':
            return self.device.device_data[self.device_id]['serial_number'] is not None
        if self._sensor_type == 'health' and self.device.device_data[self.device_id][
            'component_wifi_test_passed'] is not None:
            # if we received any data from API check the self check results
            tests_passed = (self.device.device_data[self.device_id]['component_wifi_test_passed'] and
                            self.device.device_data[self.device_id]['component_co_test_passed'] and
                            self.device.device_data[self.device_id]['component_smoke_test_passed'] and
                            self.device.device_data[self.device_id]['component_speaker_test_passed'] and
                            self.device.device_data[self.device_id]['component_led_test_passed'])
            # if we haven't received yet the valid timestamp from API, its all we can work with
            if not isinstance(self.device.device_data[self.device_id]['replace_by_date_utc_secs'], str):
                return not tests_passed

            # parse device replacement due date
            dateTimeNow = datetime.utcnow()
            dateTimeReplaceBy = datetime.fromisoformat(
                self.device.device_data[self.device_id]['replace_by_date_utc_secs'])
            # check if the device is healthy and its replacement is not due
            if tests_passed and (dateTimeReplaceBy < dateTimeNow):
                return False
            else:
                return True

        return None

    def update(self):
        """Get the latest data from the 'Protect' and updates the states."""
        self.device.update()

        if self._sensor_type == 'health':
            self._attr_extra_state_attributes = {
                "component_wifi_test_passed": self.device.device_data[self.device_id]['component_wifi_test_passed'],
                "component_co_test_passed": self.device.device_data[self.device_id]['component_co_test_passed'],
                "component_smoke_test_passed": self.device.device_data[self.device_id]['component_smoke_test_passed'],
                "component_speaker_test_passed": self.device.device_data[self.device_id][
                    'component_speaker_test_passed'],
                "component_led_test_passed": self.device.device_data[self.device_id]['component_led_test_passed'],
                "last_audio_self_test_end_utc_secs": self.device.device_data[self.device_id][
                    'last_audio_self_test_end_utc_secs'],
            }

        if self._sensor_type == 'device':
            power_source = "Unknown"
            if self.device.device_data[self.device_id]['wired_or_battery'] == 0:
                power_source = "Wired"
            if self.device.device_data[self.device_id]['wired_or_battery'] == 1:
                power_source = "Battery Operated"

            self._attr_extra_state_attributes = {
                "manufactured_on": self.device.device_data[self.device_id]['device_born_on_date_utc_secs'],
                "replace_by": self.device.device_data[self.device_id]['replace_by_date_utc_secs'],
                "serial_number": self.device.device_data[self.device_id]['serial_number'],
                "power_source": power_source,
            }

    @property
    def device_class(self):
        """Return the class of this sensor, from BinarySensorDeviceClass."""
        value = None

        if self._sensor_type == SENSOR_SMOKE_STATUS:
            value = BinarySensorDeviceClass.SMOKE.value
        if self._sensor_type == SENSOR_CO_STATUS:
            value = BinarySensorDeviceClass.GAS.value
        if self._sensor_type == BINARY_SENSOR_MOTION:
            value = BinarySensorDeviceClass.MOTION.value
        if self._sensor_type == BINARY_SENSOR_OCCUPANCY:
            value = BinarySensorDeviceClass.OCCUPANCY.value
        if self._sensor_type == BINARY_SENSOR_LINE_POWER:
            value = BinarySensorDeviceClass.POWER.value
        if self._sensor_type == "health":
            value = BinarySensorDeviceClass.PROBLEM.value
        if self._sensor_type == "device":
            value = BinarySensorDeviceClass.CONNECTIVITY.value

        return value
