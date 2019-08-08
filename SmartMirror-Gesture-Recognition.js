/**
 * @file smartmirror-gesture-recognition.js
 *
 * @author nkucza
 * @license MIT
 *
 * @see  https://github.com/NKucza/smartmirror-gesture-recognition
 */

Module.register('SmartMirror-Gesture-Recognition',{

	defaults: {
		// camera image size. This module has no image output!
		image_height: 1080,
		image_width: 1920,
		// path to appsink of gstreamer.
		image_stream_path: "/dev/shm/camera_image"	
	},

	start: function() {
		this.time_of_last_greeting_personal = [];
		this.time_of_last_greeting = 0;
		this.last_rec_user = [];
		this.current_user = null;
		this.sendSocketNotification('CONFIG', this.config);
		Log.info('Starting module: ' + this.name);
	},

	notificationReceived: function(notification, payload, sender) {
		if(notification === 'smartmirror-gesture-recognitionSetFPS') {
			this.sendSocketNotification('GestureRecognition_SetFPS', payload);
        }
	},


	socketNotificationReceived: function(notification, payload) {
		var self = this;
		if(notification === 'DETECTED_GESTURES') {
			this.sendNotification('DETECTED_GESTURES', payload);
			//console.log("[" + this.name + "] " + "gesture detected: " + payload);
        }else if (notification === 'GESTURE_DET_FPS') {
			this.sendNotification('GESTURE_DET_FPS', payload);
		};
	}
});
