#!/usr/bin/python

from __future__ import print_function
import sys
import re
from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils
from operator import add
import json


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: kafka-direct-iotmsg.py <broker_list> <topic>", file=sys.stderr)
        exit(-1)

    sc = SparkContext(appName="IoT")
    ssc = StreamingContext(sc, 3)

    brokers, topic = sys.argv[1:]
    kvs = KafkaUtils.createDirectStream(ssc, [topic], {"metadata.broker.list": brokers})

    # Read in the Kafka Direct Stream into a TransformedDStream
    jsonRDD = kvs.map(lambda (k,v): json.loads(v))
    

    ##### Processing #####

    # Average temperature in each state 
    avgTempByState = jsonRDD.map(lambda x: (x['state'], (x['payload']['data']['temperature'], 1))) \
                 .reduceByKey(lambda a,b: (a[0]+b[0], a[1]+b[1])) \
                 .map(lambda x: (x[0], x[1][0]/x[1][1])) 
    sortedTemp = avgTempByState.transform(lambda x: x.sortBy(lambda y: y[1], False))
    sortedTemp.pprint(num=100000)

    # total number of messages
    messageCount = jsonRDD.map(lambda x: 1) \
                         .reduce(add) \
                         .map(lambda x: "Total number of messages: "+ unicode(x))
    messageCount.pprint()


    # Number of devices in each state
    numSensorsByState = jsonRDD.map(lambda x: (x['state'] + ":" + x['guid'], 1)) \
                        .reduceByKey(lambda a,b: a*b) \
                        .map(lambda x: (re.sub(r":.*", "", x[0]), x[1])) \
                        .reduceByKey(lambda a,b: a+b)
    sortedSensorCount = numSensorsByState.transform(lambda x: x.sortBy(lambda y: y[0], True))
    sortedSensorCount.pprint(num=10000)

    # total number of devices
    sensorCount = jsonRDD.map(lambda x: (x['guid'], 1)) \
                         .reduceByKey(lambda a,b: a*b) \
                         .map(lambda x: 1) \
                         .reduce(add) \
                         .map(lambda x: "Total number of sensors: " + unicode(x))
    sensorCount.pprint(num=10000)


    ssc.start()
    ssc.awaitTermination()


