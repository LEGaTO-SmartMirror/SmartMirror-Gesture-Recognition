# Smartmirror-Gesture-Recognition

Uses the camera stream of the [SmartMirror-Camera-Publisher](https://github.com/LEGaTO-SmartMirror/SmartMirror-Camera-Publisher), which creates a appsink under /dev/shm/camera_image .
It returns a json object with the position, tracking id and name of each detected gesture to the scope "DETECTED_GESTURES".

An example for the json object can be seen below:

{"DETECTED_OBJECTS": [{"TrackID": 1.0, "center": [0.12593, 0.7125], "name": "flat_right", "w_h": [0.2463, 0.15417]}, {"TrackID": 3.0, "center": [0.18889, 0.79167], "name": "two_left", "w_h": [0.10741, 0.1724]}]}

# Module Config

Here you can see an example config entrie.

```
{
	module: 'SmartMirror-Gesture-Recognition',
	config: {
		// camera image size. This module has no image output!
		image_height: 1080,
		image_width: 1920,
		// path to appsink of gstreamer.
		image_stream_path: "/dev/shm/camera_image"
   	}
} 
```


## ACKNOWLEDGEMENT

This work has been supported by EU H2020 ICT project LEGaTO, contract #780681.
