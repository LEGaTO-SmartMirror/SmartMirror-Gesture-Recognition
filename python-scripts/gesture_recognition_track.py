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

from sort import *

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning) 

def shutdown(self, signum):
	cap.release()
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

#Full HD image as default
IMAGE_HEIGHT = 416
IMAGE_WIDTH = 416
IMAGE_STREAM_PATH = "/dev/shm/camera_small"

try:
	to_node("status", "starting with config: " + sys.argv[1])
	config = json.loads(sys.argv[1])
	if 'image_height' in config:
		IMAGE_HEIGHT = int(config['image_height'])
	if 'image_width' in config:
		IMAGE_WIDTH = int(config['image_width'])
	if 'image_stream_path' in config:
		IMAGE_STREAM_PATH = str(config['image_stream_path'])
		
except:
	to_node("status", "starting without config as it was not readable/existent")	

global global_FPS
global_FPS = 30.0
achieved_FPS = 0.0
achieved_FPS_counter = 0.0

def check_stdin():
	global global_FPS
	while True:
		lines = sys.stdin.readline()
		data = json.loads(lines)
		to_node("status", "Changing: " + json.dumps(data))
		if 'FPS' in data:
			global_FPS = data['FPS']

def convertBack(x, y, w, h):
    xmin = int(round(x - (w / 2)))
    xmax = int(round(x + (w / 2)))
    ymin = int(round(y - (h / 2)))
    ymax = int(round(y + (h / 2)))
    return xmin, ymin, xmax, ymax

def convertToCenterWH(a,b,c,d):
	h = float(d - b)
	w = float(c - a)
	x = float((a + (w/2)) / IMAGE_WIDTH)
	y = float((b + (h/2)) / IMAGE_HEIGHT)

	return (x,y),(w/IMAGE_WIDTH,h/IMAGE_HEIGHT)


if __name__ == "__main__":

	darknet.set_gpu(1)


	BASE_DIR = os.path.dirname(__file__) + '/'
	os.chdir(BASE_DIR)


	to_node("status", "Gesture detection is starting...")

	""" 
	get image from gestreamer appsink!
	"""
	cap = cv2.VideoCapture("shmsrc socket-path=" + str(IMAGE_STREAM_PATH) + " ! video/x-raw, format=BGR, width=" + str(IMAGE_WIDTH) + ", height=" + str(IMAGE_HEIGHT) + ", framerate=30/1 ! videoconvert ! video/x-raw, format=BGR ! appsink drop=true", cv2.CAP_GSTREAMER)
	#cap = cv2.VideoCapture(3)
	#cap.set(3,1920);
	#cap.set(4,1080);
	#cv2.namedWindow("gesture recognition tracked", cv2.WINDOW_NORMAL)

	"""
	preparare darknet neural network for hand gesture recognition
	"""

	

	configPath = "cfg/yolov3-handtracing.cfg"
	weightPath = "data/yolov3-handtracing_91_percent.weights"	
	metaPath = "data/hand.data"

	thresh = 0.6
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

	#raster for hand tracing..
	horizontal_division = 270.0
	vertical_division =  480.0

	to_node("status", "Gesture detection started...")

	darknet_image = darknet.make_image(darknet.network_width(netMain), darknet.network_height(netMain),3)

	tracker_sort = {}
	last_detection_list = []

	while True:

		start_time = time.time()

		FPS = global_FPS

		if FPS == 0:
			time.sleep(1)
			to_node("GESTURE_DET_FPS", float("{0:.2f}".format(0.0)))
			continue

		ret, frame = cap.read()
		if ret is False:
			to_node("status", "ret was false..")
			continue

		

		if (darknet.network_width(netMain) != IMAGE_WIDTH) or ( darknet.network_width(netMain) != IMAGE_HEIGHT):

			imgUMat = cv2.UMat(frame)

			frame_resized_tmp = cv2.resize(	imgUMat, 
					(darknet.network_width(netMain),
					darknet.network_height(netMain)),                                    						interpolation=cv2.INTER_LINEAR)
		
			frame_rgb = cv2.cvtColor(frame_resized_tmp, cv2.COLOR_BGR2RGB)

			frame_resized = cv2.UMat.get(frame_rgb)

		else:

			#frame_resized = cv2.UMat.get(cv2.cvtColor(imgUMat, cv2.COLOR_BGR2RGB))
			frame_resized = frame

		#frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
		#frame_resized = cv2.resize(frame_rgb,(darknet.network_width(netMain),darknet.network_height(netMain)),interpolation=cv2.INTER_LINEAR)

		darknet.copy_image_from_bytes(darknet_image,frame_resized.tobytes())

		dets = darknet.detect_image(netMain, metaMain, darknet_image, thresh=thresh)

		tracking_dets = {}

		for det in dets:
			x, y, w, h = det[2][0],\
            det[2][1],\
            det[2][2],\
            det[2][3]

			x = x / darknet.network_width(netMain) * IMAGE_WIDTH
			y = y / darknet.network_height(netMain) * IMAGE_HEIGHT
			w = w / darknet.network_width(netMain) * IMAGE_WIDTH
			h = h / darknet.network_height(netMain) * IMAGE_HEIGHT

			xmin, ymin, xmax, ymax = convertBack(
            float(x), float(y), float(w), float(h))
			pt1 = (xmin, ymin)
			pt2 = (xmax, ymax)

			for j in range(metaMain.classes):
				if det[0] == metaMain.names[j]:
					i = j
					if not i in tracking_dets :
						tracking_dets[i] = []
					tracking_dets[i].append([pt1[0],pt1[1],pt2[0],pt2[1],int(100 * det[1])])
					break


		detection_list = []

		for key in tracking_dets:
			if not key in tracker_sort:
				tracker_sort[key] = Sort(25,3)

			trackers = tracker_sort[key].update(np.asarray(tracking_dets[key]))

			for tracker in trackers:
				#cv2.rectangle(frame, (int(tracker[0]), int(tracker[1])), (int(tracker[2]), int(tracker[3])), color=(255,50,50), thickness=2)
				#cv2.putText(frame, "TrackID: " + str(tracker[4]), (int(tracker[0]), int(tracker[1])-40), cv2.FONT_HERSHEY_DUPLEX, fontScale=1,color=(255, 50, 50), thickness=3)
				#cv2.putText(frame, metaMain.names[key].decode('utf-8'), (int(tracker[0]), int(tracker[3] + 20)), cv2.FONT_HERSHEY_DUPLEX, fontScale=1, color=(255, 50, 50), thickness=3)

				center_ptr, w_h = convertToCenterWH(int(tracker[0]),int(tracker[1]),int(tracker[2]),int(tracker[3]))

				xrel = int(center_ptr[0] * horizontal_division)
				yrel = int(center_ptr[1] * vertical_division)

				detection_list.append({"TrackID": tracker[4] , "name": metaMain.names[key].decode('utf-8'), "w_h": (float("{0:.5f}".format(w_h[0])),float("{0:.5f}".format(w_h[1]))) ,"center": (float("{0:.5f}".format(xrel/horizontal_division)),float("{0:.5f}".format(yrel/vertical_division)))} )

		for key in tracker_sort:
			if not key in tracking_dets:
				trackers = tracker_sort[key].update([])

				for tracker in trackers:
					#cv2.rectangle(frame, (int(tracker[0]), int(tracker[1])), (int(tracker[2]), int(tracker[3])), color=(255,50,50), thickness=2)
					#cv2.putText(frame, "TrackID: " + str(tracker[4]), (int(tracker[0]), int(tracker[1])-40), cv2.FONT_HERSHEY_DUPLEX, fontScale=1,color=(255, 50, 50), thickness=3)
					#cv2.putText(frame, metaMain.names[key].decode('utf-8'), (int(tracker[0]), int(tracker[3] + 20)), cv2.FONT_HERSHEY_DUPLEX, fontScale=1, color=(255, 50, 50), thickness=3)

					center_ptr, w_h = convertToCenterWH(int(tracker[0]),int(tracker[1]),int(tracker[2]),int(tracker[3]))

					xrel = int(center_ptr[0] * horizontal_division)
					yrel = int(center_ptr[1] * vertical_division)

					detection_list.append({"TrackID": tracker[4] , "name": metaMain.names[key].decode('utf-8'), "w_h": (float("{0:.5f}".format(w_h[0])),float("{0:.5f}".format(w_h[1]))) ,"center": (float("{0:.5f}".format(xrel/horizontal_division)),float("{0:.5f}".format(yrel/vertical_division)))} )


		to_node("DETECTED_GESTURES",detection_list)
		"""
		if not(not last_detection_list and not detection_list):		
	
			equality_counter = 0
			for prev_element in last_detection_list:
				for next_element in detection_list:
					if next_element["center"] == prev_element["center"] and next_element["name"] == prev_element["name"]:
						equality_counter += 1
			
			if not (equality_counter == len(last_detection_list) == len(detection_list)):
				to_node("DETECTED_GESTURES",detection_list)
				last_detection_list = detection_list
		"""		
				

		achieved_FPS_counter += 1.0
		delta = time.time() - start_time


		if (1.0 / FPS) - delta > 0:
			time.sleep((1.0 / FPS) - delta)
			fps_cap = FPS
			achieved_FPS += (1.0 / FPS)
		else:
			fps_cap = 1. / delta
			achieved_FPS +=  delta

		if achieved_FPS_counter > FPS:
			to_node("GESTURE_DET_FPS", float("{0:.2f}".format(1 / (achieved_FPS / achieved_FPS_counter))))
			achieved_FPS_counter = 0.0
			achieved_FPS = 0.0

		#cv2.putText(frame, str(round(fps_cap)) + " FPS", (50, 100), cv2.FONT_HERSHEY_DUPLEX, fontScale=1, color=(50,255,50), thickness=3)

		#cv2.imshow("gesture recognition tracked", frame)
	
		#cv2.waitKey(33)
