#!/usr/bin/env bash

cd ~/Applications/confluent-3.2.2/bin

for number in {1..10}
do
printf '{\"field1\": \"'$number'\", \"field2\": \"dddff1\"}' | ./kafka-avro-console-producer \
         --broker-list localhost:9092 --topic TestTopic \
         --property value.schema='{"type":"record","name":"TestRecord","fields":[{"name":"field1","type":"string"}, {"name":"field2","type":"string"}]}'
done
exit 0