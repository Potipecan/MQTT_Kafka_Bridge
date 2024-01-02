# MQTT - Kafka two-way bridge
A simple python program that passes messages between a Kafka and an MQTT broker.

## Configuration parameters
Parameter use priority: CLI parameter, Environment variable, default value

| CLI parameter               | Environment variable          | Description                                                                 | Default value       |
|-----------------------------|-------------------------------|-----------------------------------------------------------------------------|---------------------|
| --mqtt-client-id            | MKB_MQTT_CLIENT_ID            | Name of the MQTT client used when connecting to the MQTT broker.            | "mqtt-kafka-bridge" |
| --mqtt-broker-address       | MKB_MQTT_BROKER_ADDRESS       | Address of the MQTT broker.                                                 | "localhost"         |
| --mqtt-broker-port          | MKB_MQTT_BROKER_PORT          | Port of the MQTT broker.                                                    | 1883                |
| --mqtt-username             | MKB_MQTT_USERNAME             | (Optional) MQTT client username.                                            | Not set             |
| --mqtt-password             | MKB_MQTT_PASSWORD             | (Optional, if set, mqtt-username must be set as well) MQTT client password. | Not set             |
| --mqtt-qos                  | MKB_MQTT_QOS                  | MQTT quality of service level.                                              | 2                   |
| --kafka-client-id           | MKB_KAFKA_CLIENT_ID           | Name of the Kafka clients used when connecting to the Kafka broker.         | "mqtt-kafka-bridge  |
| --kafka-broker-address      | MKB_KAFKA_BROKER_ADDRESS      | Listener address of the Kafka broker.                                       | "localhost"         |
| --kafka-broker-port         | MKB_KAFKA_BROKER_PORT         | Listener port of the Kafka broker.                                          | 9092                |
| --mqtt-kafka-topic-mappings | MKB_MQTT_KAFKA_TOPIC_MAPPINGS | MQTT to Kafka topic mappings.                                               | Not set             |
| --kafka-mqtt-topic-mappings | MKB_KAFKA_MQTT_TOPIC_MAPPINGS | Kafka to MQTT topic mappings.                                               | Not set             |

## Topic mappings

Topics are mapped as **source_topic**>>**target_topic** separated by **|** (bar).

In --mqtt-kafka-topic-mappings setting, source topic is the MQTT topic where the message originates from, and target topic is the Kafka topic where the message will be sent.
In --kafka-mqtt-topic-mappings it's the other way around.

Either one or both of the settings must be set for the bridge to run. If both are set, you must make sure you don't make loops, or the bridge won't run.

## Examples
See [examples/fullstack](https://github.com/Potipecan/MQTT_Kafka_Bridge/tree/master/examples/fullstack).
