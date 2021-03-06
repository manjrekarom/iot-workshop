import threading
import time
import json
import ast
import RPi.GPIO as GPIO
import sys
import Adafruit_DHT
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

# Details about thing
# TODO: Change settings
THING_ID = "thing50"
CLIENT_ID = "MyRpi50"
CERTIFICATE_PATH = "./certificates"
ENDPOINT = "a221a6r4ojicsi.iot.ap-southeast-1.amazonaws.com"

# LED PINs
# TODO: Change pins [if required]
LED_PIN_1 = 17 # 11 R but B
LED_PIN_2 = 27 # 13 G but G
LED_PIN_3 = 22 # 15 B but R

# Temperature and humidity sensor
DHT_PIN = 21

# Device ids
LED_ID = "device88.254"

TEMP_ID = "device85.247"
HUMID_ID = "device85.248"


# Initialize GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN_1, GPIO.OUT)
GPIO.setup(LED_PIN_2, GPIO.OUT)
GPIO.setup(LED_PIN_3, GPIO.OUT)
GPIO.setup(SERVO_PIN_1, GPIO.OUT)
GPIO.setup(SERVO_PIN_2, GPIO.OUT)

# Change to your topics here
UPDATE_TOPIC = "$aws/things/" + THING_ID + "/shadow/update"
DELTA_TOPIC = "$aws/things/" + THING_ID + "/shadow/update/delta"

ROOT_CA = CERTIFICATE_PATH + "/rootCA.pem"
PRIVATE_KEY = CERTIFICATE_PATH + "/private.key.pem"
CERTIFICATE_CRT = CERTIFICATE_PATH + "/certificate.crt.pem"

sensor = Adafruit_DHT.DHT11


def get_init_mqtt_client(): 
	# Configuration for AWS IoT
	myMQTTClient = AWSIoTMQTTClient(CLIENT_ID)
	myMQTTClient.configureEndpoint(ENDPOINT, 8883)
	myMQTTClient.configureCredentials(ROOT_CA, PRIVATE_KEY, CERTIFICATE_CRT)


	# myMQTTClient.configureOfflinePublishQueueing(-1)  
	# Infinite offline Publish queueing
	# myMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
	myMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
	myMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec
	myMQTTClient.enableMetricsCollection()

	return myMQTTClient



def publish_continuously(interval, mqtt_client, servo1, servo2):
	while True:
		publish_sensor_data(mqtt_client, servo1, servo2)
		time.sleep(interval)



def publish_sensor_data(mqtt_client, servo1, servo2):	
	# Dictionaries and messages for publishing
	humidity, temperature = Adafruit_DHT.read_retry(sensor, DHT_PIN)
	# TODO: Change the dictionary keys to keys of the device shadow JSON 
	publish_dict = {'state': {'reported': {LED_ID: get_led_values(), 
	TEMP_ID: temperature,
	HUMID_ID: humidity
	}}}

	publish_message = json.dumps(publish_dict)
	print "Message to publish:-", publish_message

	# Update device shadow
	published = mqtt_client.publish(UPDATE_TOPIC, publish_message, 0)
	print "Published:-", published



def update_thing_state(client, userdata, message):
	print client, userdata, message
	message_dict = ast.literal_eval(message.payload)

	state = message_dict['state']
	print state

	# TODO: Change the dictionary keys to keys of the device shadow JSON
	# Change to your LED device 
	print "len of arguments ", len(sys.argv[1:])
	if len(sys.argv[1:]):
		if sys.argv[1] == "--relay":
			if LED_ID in state:
				led = message_dict['state'][LED_ID]
				print led
				if led == "BLUE":
					GPIO.output(LED_PIN_1, False)
					GPIO.output(LED_PIN_2, False)
					GPIO.output(LED_PIN_3, False)
				elif led == "GREEN":
					GPIO.output(LED_PIN_1, True)
					GPIO.output(LED_PIN_2, True)
					GPIO.output(LED_PIN_3, False)
				elif led == "RED":
					GPIO.output(LED_PIN_1, True)
					GPIO.output(LED_PIN_2, False)
					GPIO.output(LED_PIN_3, True)
				elif led == "OFF":
					GPIO.output(LED_PIN_1, True)
					GPIO.output(LED_PIN_2, False)
					GPIO.output(LED_PIN_3, False)
	else: # if no cmd line arguments then run default LED loop
		if LED_ID in state:
			led = message_dict['state'][LED_ID]
			print led
			if led == "BLUE":
				GPIO.output(LED_PIN_1, True)
				GPIO.output(LED_PIN_2, False)
				GPIO.output(LED_PIN_3, False)
			elif led == "GREEN":
				GPIO.output(LED_PIN_1, False)
				GPIO.output(LED_PIN_2, True)
				GPIO.output(LED_PIN_3, False)
			elif led == "RED":
				GPIO.output(LED_PIN_1, False)
				GPIO.output(LED_PIN_2, False)
				GPIO.output(LED_PIN_3, True)
			elif led == "OFF":
				GPIO.output(LED_PIN_1, False)
				GPIO.output(LED_PIN_2, False)
				GPIO.output(LED_PIN_3, False)
	
	# push updated state
	# publish_sensor_data(mqtt_client, servo1, servo2)


def get_led_values():
	if len(sys.argv[1:]):
		if sys.argv[1] == "--relay": 
			if GPIO.input(LED_PIN_1) == False:
				led = "BLUE"
			elif GPIO.input(LED_PIN_2):
				led = "GREEN"
			elif GPIO.input(LED_PIN_3):
				led = "RED"
			else:
				led = "OFF"
	else:
		if GPIO.input(LED_PIN_1):
			led = "BLUE"
		elif GPIO.input(LED_PIN_2):
			led = "GREEN"
		elif GPIO.input(LED_PIN_3):
			led = "RED"
		else:
			led = "OFF"
	return led 



if __name__ == "__main__":
	try:
		# Connect to MQTT broker
		mqtt_client = get_init_mqtt_client()

		print "Connected:-", mqtt_client.connect()
		
		# Start the thread
		t = threading.Thread(target=publish_continuously, args = (5, mqtt_client, 
			servo1, servo2))
		

		# Run the thread as a daemon which will die after parent dies 
		t.daemon = True
		t.start()
		
		mqtt_client.subscribe(DELTA_TOPIC, 0, update_thing_state)
		
		# To keep parent alive as long as ctrl + c
		while True:
			pass
	except KeyboardInterrupt:
		print "Cleaning up and exiting!"
		servo1.stop()
		servo2.stop()
		GPIO.cleanup()
