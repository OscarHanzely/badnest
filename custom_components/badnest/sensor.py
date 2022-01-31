import logging

from homeassistant.helpers.entity import Entity

from .const import DOMAIN

from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_CO,
    DEVICE_CLASS_BATTERY,
    TEMP_CELSIUS
)

_LOGGER = logging.getLogger(__name__)

PROTECT_SENSOR_TYPES = [
    "co_status",
    "smoke_status",
    "battery_health_state",
    "battery_level",
    "auto_away",
    "line_power_present",
    "home_away_input",
    "health",
]


async def async_setup_platform(hass,
                               config,
                               async_add_entities,
                               discovery_info=None):
    """Set up the Nest climate device."""
    api = hass.data[DOMAIN]['api']

    temperature_sensors = []
    _LOGGER.info("Adding temperature sensors")
    for sensor in api['temperature_sensors']:
        _LOGGER.info(f"Adding nest temp sensor uuid: {sensor}")
        temperature_sensors.append(NestTemperatureSensor(sensor, api))

    async_add_entities(temperature_sensors)

    protect_sensors = []
    _LOGGER.info("Adding protect sensors")
    for sensor in api['protects']:
        _LOGGER.info(f"Adding nest protect sensor uuid: {sensor}")
        for sensor_type in PROTECT_SENSOR_TYPES:
            protect_sensors.append(NestProtectSensor(sensor, sensor_type, api))

    async_add_entities(protect_sensors)


class NestTemperatureSensor(Entity):
    """Implementation of the Nest Temperature Sensor."""

    def __init__(self, device_id, api):
        """Initialize the sensor."""
        self._name = "Nest Temperature Sensor"
        self._unit_of_measurement = TEMP_CELSIUS
        self.device_id = device_id
        self.device = api

    @property
    def unique_id(self):
        """Return an unique ID."""
        return self.device_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return self.device.device_data[self.device_id]['name']

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.device.device_data[self.device_id]['temperature']

    @property
    def device_class(self):
        """Return the device class of this entity."""
        return DEVICE_CLASS_TEMPERATURE

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    def update(self):
        """Get the latest data from the DHT and updates the states."""
        self.device.update()

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_BATTERY_LEVEL:
                self.device.device_data[self.device_id]['battery_level']
        }


class NestProtectSensor(Entity):
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
                "device_born_on_date_utc_secs": None,
                "replace_by_date_utc_secs": None,
                "serial_number": None,
                "wired_or_battery": None,
            }
            _LOGGER.debug(
                "Created entity for health"
            )

    @property
    def unique_id(self):
        """Return an unique ID."""
        return self.device_id + '_' + self._sensor_type

    @property
    def name(self):
        """Return the name of the sensor."""
        return self.device.device_data[self.device_id]['name'] + \
               f' {self._sensor_type}'

    @property
    def state(self):
        """Return the state of the sensor."""
        result = None

        if self._sensor_type == 'health':
            if (self.device.device_data[self.device_id]['component_wifi_test_passed'] and
                    self.device.device_data[self.device_id]['component_co_test_passed'] and
                    self.device.device_data[self.device_id]['component_smoke_test_passed'] and
                    self.device.device_data[self.device_id]['component_speaker_test_passed'] and
                    self.device.device_data[self.device_id]['component_led_test_passed']):
                result = 'OK'
            else:
                result = 'Test failure'
        else:
            result = self.device.device_data[self.device_id][self._sensor_type]

        return result

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
                "device_born_on_date_utc_secs": self.device.device_data[self.device_id]['device_born_on_date_utc_secs'],
                "replace_by_date_utc_secs": self.device.device_data[self.device_id]['replace_by_date_utc_secs'],
                "serial_number": self.device.device_data[self.device_id]['serial_number'],
                "wired_or_battery": self.device.device_data[self.device_id]['wired_or_battery'],
            }
            _LOGGER.debug(
                "Updated extra attributes"
            )

    @property
    def device_class(self):
        """Return the class of this sensor, from DEVICE_CLASSES."""
        # https://github.com/home-assistant/core/blob/dev/homeassistant/const.py#L273
        value = None

        if self._sensor_type == 'battery_level':
            value = DEVICE_CLASS_BATTERY
        if self._sensor_type == 'co_status':
            value = DEVICE_CLASS_CO

        return value
