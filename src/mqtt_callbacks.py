import paho.mqtt.client as mqtt


def mqtt_on_connect(client: mqtt.Client, userdata, flags, rc) -> None:
    print("MQTT connected with result code " + str(rc))


def mqtt_on_disconnect(client: mqtt.Client, userdata, rc):
    print("MQTT disconnected with result code " + str(rc))


def mqtt_on_subscribe(client: mqtt.Client, userdata, mid, granted_qos: int) -> None:
    pass


def mqtt_on_unsubscribe(client: mqtt.Client, userdata, mid):
    pass


def mqtt_on_publish(client: mqtt.Client, userdata, mid: int) -> None:
    pass


def mqtt_on_log(client: mqtt.Client, userdata, level, buf) -> None:
    pass
