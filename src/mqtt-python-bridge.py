import paho.mqtt.client as mqtt
import kafka
import kafka.errors as k_errors
import argparse
import os
from mqtt_callbacks import *
import signal
import threading
from logging import log
import logging

mqtt_kafka_topic_mapping: dict[str, str] | None = None
kafka_mqtt_topic_mapping: dict[str, str] | None = None
mqtt_client: mqtt.Client | None = None
kafka_producer: kafka.KafkaProducer | None = None
kafka_consumer: kafka.KafkaConsumer | None = None
kafka_consumer_thread: threading.Thread | None = None
kafka_consumer_stop_event = threading.Event()


def parse_topic_mappings(topic_mappings: str) -> dict[str, str]:
    topic_mappings_split = topic_mappings.split("|")
    if len(topic_mappings_split) == 0:
        raise ValueError(f"Invalid topic mappings: {topic_mappings}")

    in_out_map = {}

    for mapping in topic_mappings_split:
        topic_split = mapping.split(">>")
        if len(topic_split) != 2:
            raise ValueError(f"Invalid mapping {mapping}")
        mqtt_topic, kafka_topic = topic_split

        in_out_map[mqtt_topic] = kafka_topic

    return in_out_map


def print_mappings(mappings: dict[str, str], offset: int | str = 5) -> None:
    if type(offset) is int:
        offset = " " * offset
    elif not type(offset) is str:
        raise TypeError(f"Invalid type of offset {type(offset)}")
    for topic, mapping in mappings.items():
        print(f"{offset}{topic} >> {mapping}")


def get_config():
    parser = argparse.ArgumentParser("MQTT-Kafka Bridge",
                                     description="A bridge between mqtt and kafka brokers",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--mqtt-client_id", type=str,
                        default=os.environ.get("MKB_MQTT_CLIENT_ID", "mqtt-kafka-bridge"))
    parser.add_argument("--mqtt-broker-address", type=str,
                        default=os.environ.get("MKB_MQTT_BROKER_ADDRESS", "localhost"))
    parser.add_argument("--mqtt-broker-port", type=int,
                        default=int(os.environ.get("MKB_MQTT_BROKER_PORT", 1883)))
    parser.add_argument("--mqtt-username", type=str,
                        default=os.environ.get("MKB_MQTT_USERNAME"))
    parser.add_argument("--mqtt-password", type=str,
                        default=os.environ.get("MKB_MQTT_PASSWORD"))
    parser.add_argument("--mqtt-qos", type=int,
                        default=int(os.environ.get("MKB_MQTT_QOS", 2)))

    parser.add_argument("--kafka-client-id", type=str,
                        default=os.environ.get("MKB_KAFKA_CLIENT_ID", "mqtt-kafka-bridge"))
    parser.add_argument("--kafka-broker-address", type=str,
                        default=os.environ.get("MKB_KAFKA_BROKER_ADDRESS", "localhost"))
    parser.add_argument("--kafka-broker-port", type=int,
                        default=int(os.environ.get("MKB_KAFKA_BROKER_PORT", 9092)))

    parser.add_argument("--mqtt-kafka-topic-mappings", type=parse_topic_mappings,
                        default=os.environ.get("MKB_MQTT_KAFKA_TOPIC_MAPPINGS"))
    parser.add_argument("--kafka-mqtt-topic-mappings", type=parse_topic_mappings,
                        default=os.environ.get("MKB_KAFKA_MQTT_TOPIC_MAPPINGS"))

    args = parser.parse_args()

    # print settings
    args_string = str(args)
    start = 10
    end = len(args_string) - 1
    args_string = args_string[start:end].replace(", ", "\n")
    log(logging.INFO, "Bridge configuration:\n%s", args_string)

    t_flag = 0
    if args.mqtt_kafka_topic_mappings is not None:
        t_flag += 1
    if args.kafka_mqtt_topic_mappings is not None:
        t_flag += 2
    if t_flag == 0:
        log(logging.ERROR, "Neither MQTT to Kafka or Kafka to MQTT topic mappings are set.")
        clean_exit(1)
    if t_flag & 1:
        log(logging.INFO, "MQTT to Kafka topic mappings set:")
        print_mappings(args.mqtt_kafka_topic_mappings, 5)
    if t_flag & 2:
        log(logging.INFO, "Kafka to MQTT topic mappings set:")
        print_mappings(args.kafka_mqtt_topic_mappings, 5)
    if t_flag == 3:
        for key, value in args.mqtt_kafka_topic_mappings.items():
            if args.kafka_mqtt_topic_mappings.get(value) == key:
                log(logging.ERROR, "Topic mapping loop detected: %s <> %s", key, value)
                clean_exit(2)

    return args


def init_mqtt_client(client_id: str, username: str | None = None, password: str | None = None) -> None:
    global mqtt_kafka_topic_mapping, mqtt_client
    mqtt_client = mqtt.Client(client_id, False)
    if username is not None:
        mqtt_client.username_pw_set(password=password, username=username)

    mqtt_client.on_log = mqtt_on_log
    mqtt_client.on_connect = mqtt_on_connect
    mqtt_client.enable_logger()
    mqtt_client.on_disconnect = mqtt_on_disconnect
    mqtt_client.on_message = mqtt_on_message
    return


def mqtt_on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
    global mqtt_kafka_topic_mapping, kafka_producer

    kafka_topic = mqtt_kafka_topic_mapping[msg.topic]
    kafka_producer.send(kafka_topic, msg.payload)


def mqtt_connect(server: str, port: int) -> bool:
    global mqtt_kafka_topic_mapping, mqtt_client
    if mqtt_client.connect(server, port, 1000) != mqtt.CONNACK_ACCEPTED:
        return False
    return True


def init_kafka_producer(client_id: str, server: str, port: int) -> bool:
    global kafka_producer
    log(logging.INFO, f"Initializing the Kafka producer with bootstrap server {server}:{port}.")
    try:
        kafka_producer = kafka.KafkaProducer(bootstrap_servers=f"{server}:{port}",
                                             client_id=client_id + "_producer")
    except k_errors.KafkaError as e:
        log(logging.ERROR, "Failed to initialize Kafka producer, reason: %s", e)
        return False
    return True


def init_kafka_consumer(client_id: str, server: str, port: int) -> bool:
    global kafka_consumer, kafka_mqtt_topic_mapping
    topics = [topic for topic in kafka_mqtt_topic_mapping.keys()]
    log(logging.INFO, f"Initializing the Kafka consumer with bootstrap server {server}:{port}. "
                      f"Subscribing to topics: {topics}")
    try:
        kafka_consumer = kafka.KafkaConsumer(*topics,
                                             bootstrap_servers=f"{server}:{port}",
                                             group_id=client_id,
                                             client_id=client_id + "_consumer",
                                             consumer_timeout_ms=1000,
                                             auto_offset_reset="earliest")
    except k_errors.KafkaError as e:
        log(logging.ERROR, "Failed to initialize Kafka consumer, reason: %s", e)
        return False
    return True


def kafka_to_mqtt(qos: int):
    global kafka_consumer, mqtt_client, kafka_mqtt_topic_mapping
    if kafka_consumer is None:
        raise ValueError("Kafka consumer is not initialized.")
    kafka_consumer.poll(1000)
    log(logging.INFO, "Kafka polling started")
    while not kafka_consumer_stop_event.is_set():
        for record in kafka_consumer:
            info = mqtt_client.publish(topic=kafka_mqtt_topic_mapping[record.topic],
                                       payload=record.value,
                                       qos=qos)
            if kafka_consumer_stop_event.is_set() or info.rc == mqtt.MQTT_ERR_NO_CONN:
                break
    log(logging.INFO, "Kafka polling stopped")


def clean_exit(exit_code: int) -> None:
    global mqtt_client, kafka_producer, kafka_consumer, kafka_consumer_thread, kafka_consumer_stop_event
    kafka_consumer_stop_event.set()

    if mqtt_client is not None and mqtt_client.is_connected():
        mqtt_client.disconnect()
        logging.log(logging.INFO, "MQTT client disconnected")
    if kafka_producer is not None and kafka_producer.bootstrap_connected():
        kafka_producer.close()
        log(logging.INFO, "Kafka producer connection closed")
    if kafka_consumer is not None and kafka_consumer.bootstrap_connected():
        kafka_consumer.close()
        log(logging.INFO, "Kafka consumer connection closed")
    if kafka_consumer_thread is not None and kafka_consumer_thread.is_alive():
        kafka_consumer_thread.join(timeout=1000)
        log(logging.INFO, "Kafka listener thread joined")

    logging.log(logging.INFO if exit_code == 0 else logging.CRITICAL, "Exiting with code %d", exit_code)
    exit(exit_code)


def int_signal_handler(sig, _):
    if sig == signal.SIGINT:
        clean_exit(0)


def main():
    global mqtt_kafka_topic_mapping, kafka_mqtt_topic_mapping, kafka_consumer_thread

    signal.signal(signal.SIGINT, int_signal_handler)

    config = get_config()
    mqtt_kafka_topic_mapping = config.mqtt_kafka_topic_mappings
    kafka_mqtt_topic_mapping = config.kafka_mqtt_topic_mappings

    # configuring MQTT client
    init_mqtt_client(config.mqtt_client_id, config.mqtt_username, config.mqtt_password)
    if not mqtt_connect(config.mqtt_broker_address, config.mqtt_broker_port):
        clean_exit(128)

    # configuring MQTT -> Kafka bridge
    if mqtt_kafka_topic_mapping is not None:
        subscriptions = [(topic, config.mqtt_qos) for topic in mqtt_kafka_topic_mapping.keys()]
        mqtt_client.subscribe(subscriptions)
        if not init_kafka_producer(config.kafka_client_id,
                                   config.kafka_broker_address,
                                   config.kafka_broker_port):
            clean_exit(127)

    # configuring Kafka -> MQTT bridge
    if kafka_mqtt_topic_mapping is not None:
        if not init_kafka_consumer(config.kafka_client_id,
                                   config.kafka_broker_address,
                                   config.kafka_broker_port):
            clean_exit(127)

    kafka_consumer_thread = threading.Thread(target=kafka_to_mqtt, args=[config.mqtt_qos])
    kafka_consumer_thread.start()
    mqtt_client.loop_forever()


if __name__ == '__main__':
    main()
