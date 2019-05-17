#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from ctypes import *
import math
import random
import cv2
import time , threading
import json, sys, os, signal
import numpy as np
import darknet


if os.path.exists("/tmp/gesture_recognition_captions") is True:
	os.remove("/tmp/gesture_recognition_captions")
if os.path.exists("/tmp/gesture_indicator") is True:
	os.remove("/tmp/gesture_indicator")

def shutdown(self, signum):
	out_cap.release()
	cap.release()
	#out.release()

	if os.path.exists("/tmp/gesture_recognition_captions") is True:
		os.remove("/tmp/gesture_recognition_captions")
	if os.path.exists("/tmp/gesture_indicator") is True:
		os.remove("/tmp/gesture_indicator")

	to_node("status", 'Shutdown: Done.')
	exit()

def to_node(type, message):
	# convert to json and print (node helper will read from stdout)
	try:
		print(json.dumps({type: message}))
	except Exception:
		pass
	# stdout has to be flushed manually to prevent delays in the node helper communication
	sys.stdout.flush()

FPS = 30.

def check_stdin():
	global FPS
	while True:
		lines = sys.stdin.readline()
		data = json.loads(lines)
		if 'FPS' in data:
			FPS = data['FPS']

def convertBack(x, y, w, h):
    xmin = int(round(x - (w / 2)))
    xmax = int(round(x + (w / 2)))
    ymin = int(round(y - (h / 2)))
    ymax = int(round(y + (h / 2)))
    return xmin, ymin, xmax, ymax


if __name__ == "__main__":


	BASE_DIR = os.path.dirname(__file__) + '/'
	os.chdir(BASE_DIR)


	""" 
	preparare image output for on screen visualisation 
	"""
	#out = cv2.VideoWriter('appsrc ! shmsink socket-path=/tmp/gesture_recognition_image sync=true wait-for-connection=false shm-size=100000000',0, 30, (1080,1920), True)
	out_cap = cv2.VideoWriter('appsrc ! shmsink socket-path=/tmp/gesture_recognition_captions sync=true wait-for-connection=false shm-size=100000000',0, 30, (1080,1920), True)
	out_indicator = cv2.VideoWriter('appsrc ! shmsink socket-path=/tmp/gesture_indicator sync=true wait-for-connection=false shm-size=100000000',0, 30, (1080,1920), True)

	#out.write(np.zeros((1920,1080,3), np.uint8))
	out_cap.write(np.zeros((1920,1080,3), np.uint8))
	out_indicator.write(np.zeros((1920,1080,3), np.uint8))

	to_node("status", "Gesture detection is starting...")

	""" 
	get image from gestreamer appsink!
	"""
	cap = cv2.VideoCapture("shmsrc socket-path=/tmp/camera_image ! video/x-raw, format=BGR, width=1080, height=1920, framerate=30/1 ! videoconvert ! video/x-raw, format=BGR ! appsink drop=true", cv2.CAP_GSTREAMER)
	#cap = cv2.VideoCapture("shmsrc socket-path=/tmp/camera_1m ! video/x-raw, format=BGR, width=1080, height=1920, framerate=30/1 ! videoconvert ! video/x-raw, format=BGR ! appsink drop=true", cv2.CAP_GSTREAMER)
	#cap = cv2.VideoCapture(3)
	#cap.set(3,1920);
	#cap.set(4,1080);
	#cv2.namedWindow("object detection", cv2.WINDOW_NORMAL)


	"""
	preparare darknet neural network for hand gesture recognition
	"""

	darknet.set_gpu(1)

	configPath = "cfg/yolov3-handtracing.cfg"
	#weightPath = "data/yolov3-handtracing_60172.weights"
	weightPath = "data/yolov3-handtracing_last.weights"	
	metaPath = "data/hand.data"

	thresh = 0.5
	hier_thresh=.45
	nms=.45 
	debug= False

	netMain = darknet.load_net_custom(configPath.encode("ascii"), weightPath.encode("ascii"), 0, 1)  # batch size = 1
	metaMain = darknet.load_meta(metaPath.encode("ascii"))

	"""
	start thread for standart in
	"""	
	t = threading.Thread(target=check_stdin)
	t.start()
	

	"""
	in case of shutdown
	"""
	signal.signal(signal.SIGINT, shutdown)

	#raster for hand tracing.. here the image resolution 
	horizontal_division = 18.0
	vertical_division =  32.0

	DetectionArray = np.zeros((int(vertical_division),int(horizontal_division),metaMain.classes),dtype=np.uint8)

	to_node("status", "Gesture detection started...")

	darknet_image = darknet.make_image(darknet.network_width(netMain), darknet.network_height(netMain),3)


	
	image_flat_right = cv2.imread('icons/flat_right.jpg')
	image_flat_left = cv2.imread('icons/flat_left.jpg')

	image_okay_right = cv2.imread('icons/okay_right.jpg')
	image_okay_left = cv2.imread('icons/okay_left.jpg')

	image_thumbs_up_right = cv2.imread('icons/thumbs_up_right.jpg')
	image_thumbs_up_left = cv2.imread('icons/thumbs_up_left.jpg')

	image_thumbs_down_right = cv2.imread('icons/thumbs_down_right.jpg')
	image_thumbs_down_left = cv2.imread('icons/thumbs_down_left.jpg')



	while True:

		start_time = time.time()

		ret, frame = cap.read()
		if ret is False:
			continue

		image_cap = np.zeros((1920,1080,3), np.uint8)
		image_indicator = np.zeros((1920,1080,3), np.uint8)

		frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
		frame_resized = cv2.resize(frame_rgb,
                                   (darknet.network_width(netMain),
                                    darknet.network_height(netMain)),
                                   interpolation=cv2.INTER_LINEAR)


		darknet.copy_image_from_bytes(darknet_image,frame_resized.tobytes())

		dets = darknet.detect_image(netMain, metaMain, darknet_image, thresh=0.25)

	
		DetectionArray = np.where(DetectionArray >0 , DetectionArray -1 , 0)

		for det in dets:
			x, y, w, h = det[2][0],\
            det[2][1],\
            det[2][2],\
            det[2][3]

			x = x / darknet.network_width(netMain) * 1080
			y = y / darknet.network_height(netMain) * 1920
			w = w / darknet.network_width(netMain) * 1080
			h = h / darknet.network_height(netMain) * 1920

			xmin, ymin, xmax, ymax = convertBack(
            float(x), float(y), float(w), float(h))
			pt1 = (xmin, ymin)
			pt2 = (xmax, ymax)

			for j in range(metaMain.classes):
				if det[0] == metaMain.names[j]:
					i = j
					break

	
			cv2.circle(image_cap , (int(x), int(y))  , 5,(55,55,255), 5)
			cv2.rectangle(image_cap,pt1,pt2,(55,55,255), 3)
			cv2.putText(image_cap, det[0].decode('utf-8'), (pt1[0], pt1[1] - 5), cv2.FONT_HERSHEY_DUPLEX, fontScale=1, color=(55,255,55), thickness=3)

			

			cv2.circle(frame , (int(x), int(y))  , 5,(55,55,255), 5)
			cv2.rectangle(frame ,pt1,pt2,(55,55,255), 3)
			cv2.putText(frame, det[0].decode('utf-8'), (pt1[0], pt1[1] - 5), cv2.FONT_HERSHEY_DUPLEX, fontScale=1, color=(55,255,55), thickness=3)
		

			xrel = int(x / 1080 * horizontal_division)
			yrel = int(y / 1920 * vertical_division)

			#cv2.circle(image_indicator , (int(xrel* (1080 / horizontal_division)) , int(yrel* (1920 / vertical_division)))  , 5,(55,55,255), 5)
			cpX = int(xrel* (1080 / horizontal_division))
			cpY = int(yrel* (1920 / vertical_division))


			if (det[0].decode("utf-8") == "flat_right"):
				if(cpX + image_flat_right.shape[1] > 1080):
					cpX = 1080 - image_flat_right.shape[1]
				if(cpY + image_flat_right.shape[0] > 1920):
					cpY = 1920 - image_flat_right.shape[0]

				image_indicator [cpY:cpY + image_flat_right.shape[0] , cpX:cpX + image_flat_right.shape[1]] =  image_flat_right

			if (det[0].decode("utf-8") == "flat_left"):
				if(cpX + image_flat_left.shape[1] > 1080):
					cpX = 1080 - image_flat_left.shape[1]
				if(cpY + image_flat_left.shape[0] > 1920):
					cpY = 1920 - image_flat_left.shape[0]

				image_indicator [cpY:cpY + image_flat_left.shape[0] , cpX:cpX + image_flat_left.shape[1]] =  image_flat_left

			if (det[0].decode("utf-8") == "okay_right"):
				if(cpX + image_okay_right.shape[1] > 1080):
					cpX = 1080 - image_okay_right.shape[1]
				if(cpY + image_okay_right.shape[0] > 1920):
					cpY = 1920 - image_okay_right.shape[0]

				image_indicator [cpY:cpY + image_okay_right.shape[0] , cpX:cpX + image_okay_right.shape[1]] =  image_okay_right
			
			if (det[0].decode("utf-8") == "okay_left"):
				if(cpX + image_okay_left.shape[1] > 1080):
					cpX = 1080 - image_okay_left.shape[1]
				if(cpY + image_okay_left.shape[0] > 1920):
					cpY = 1920 - image_okay_left.shape[0]

				image_indicator [cpY:cpY + image_okay_left.shape[0] , cpX:cpX + image_okay_left.shape[1]] =  image_okay_left

			if (det[0].decode("utf-8") == "thumbs_down_left"):
				if(cpX + image_thumbs_down_left.shape[1] > 1080):
					cpX = 1080 - image_thumbs_down_left.shape[1]
				if(cpY + image_thumbs_down_left.shape[0] > 1920):
					cpY = 1920 - image_thumbs_down_left.shape[0]

				image_indicator [cpY:cpY + image_thumbs_down_left.shape[0] , cpX:cpX + image_thumbs_down_left.shape[1]] =  image_thumbs_down_left

			if (det[0].decode("utf-8") == "thumbs_down_right"):
				if(cpX + image_thumbs_down_right.shape[1] > 1080):
					cpX = 1080 - image_thumbs_down_right.shape[1]
				if(cpY + image_thumbs_down_right.shape[0] > 1920):
					cpY = 1920 - image_thumbs_down_right.shape[0]

				image_indicator [cpY:cpY + image_thumbs_down_right.shape[0] , cpX:cpX + image_thumbs_down_right.shape[1]] =  image_thumbs_down_right

			if (det[0].decode("utf-8") == "thumbs_up_left"):
				if(cpX + image_thumbs_up_left.shape[1] > 1080):
					cpX = 1080 - image_thumbs_up_left.shape[1]
				if(cpY + image_thumbs_up_left.shape[0] > 1920):
					cpY = 1920 - image_thumbs_up_left.shape[0]

				image_indicator [cpY:cpY + image_thumbs_up_left.shape[0] , cpX:cpX + image_thumbs_up_left.shape[1]] =  image_thumbs_up_left

			if (det[0].decode("utf-8") == "thumbs_up_right"):
				if(cpX + image_thumbs_up_right.shape[1] > 1080):
					cpX = 1080 - image_thumbs_up_right.shape[1]
				if(cpY + image_thumbs_up_right.shape[0] > 1920):
					cpY = 1920 - image_thumbs_up_right.shape[0]

				image_indicator [cpY:cpY + image_thumbs_up_right.shape[0] , cpX:cpX + image_thumbs_up_right.shape[1]] =  image_thumbs_up_right
			


			DetectionArray[yrel,xrel,i] += 2

			if DetectionArray[yrel,xrel,i] == FPS:
				DetectionArray[yrel,xrel,i] = 0			
			if DetectionArray[yrel,xrel,i] == 2:
				to_node("detected",{"name": str(det[0].decode("utf-8")), "center": (float("{0:.5f}".format(yrel/vertical_division)),float("{0:.5f}".format(xrel/horizontal_division))),"box": (float("{0:.5f}".format(w / darknet.network_width(netMain))),float("{0:.5f}".format(w / darknet.network_width(netMain))))})

		delta = time.time() - start_time
		if (1.0 / FPS) - delta > 0:
			time.sleep((1.0 / FPS) - delta)
			fps_cap = FPS
		else:
			fps_cap = 1. / delta

		cv2.putText(frame, str(round(fps_cap)) + " FPS", (50, 100), cv2.FONT_HERSHEY_DUPLEX, fontScale=1, color=(50,255,50), thickness=3)
		cv2.putText(image_cap, str(round(fps_cap)) + " FPS", (50, 150), cv2.FONT_HERSHEY_DUPLEX, fontScale=1, color=(55,55,255), thickness=3)

		#cv2.imshow("object detection", image_indicator)

		out_cap.write(image_cap)
		out_indicator.write(image_indicator)
	
		#cv2.waitKey(33)
