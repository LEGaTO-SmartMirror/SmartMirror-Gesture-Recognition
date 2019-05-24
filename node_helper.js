'use strict';
const NodeHelper = require('node_helper');

const {PythonShell} = require('python-shell');
var pythonStarted = false

module.exports = NodeHelper.create({

	python_start: function () {
		const self = this;		

		
		self.pyshell = new PythonShell('modules/' + this.name + '/python-scripts/gesture_recognition_track.py', {pythonPath: 'python', args: [JSON.stringify(this.config)]});
    		
		self.pyshell.on('message', function (message) {
			try{
				var parsed_message = JSON.parse(message)
           		//console.log("[MSG " + self.name + "] " + message);
				if (parsed_message.hasOwnProperty('status')){
					console.log("[" + self.name + "] " + parsed_message.status);
  				}else if (parsed_message.hasOwnProperty('detected')){
					//console.log("[" + self.name + "] detected gestures: " + parsed_message);
					self.sendSocketNotification('detected', parsed_message);
				}else if (parsed_message.hasOwnProperty('DETECTED_GESTURES')){
					//console.log("[" + self.name + "] detected gestures: " + JSON.stringify(parsed_message));
					self.sendSocketNotification('DETECTED_GESTURES', parsed_message);
				}else if (parsed_message.hasOwnProperty('GESTURE_DET_FPS')){
					//console.log("[" + self.name + "] detected gestures: " + JSON.stringify(parsed_message));
					self.sendSocketNotification('GESTURE_DET_FPS', parsed_message.GESTURE_DET_FPS);
				}
			}
			catch(err) {
				console.log(message)
				//console.log(err)
			}
   		});
  	},

	//, mode: 'json'

  	// Subclass socketNotificationReceived received.
  	socketNotificationReceived: function(notification, payload) {
		const self = this;
		if(notification === 'GestureRecognition_SetFPS') {
			if(pythonStarted) {
                var data = {"FPS": payload}
                self.pyshell.send(JSON.stringify(data));

            }
        }else if(notification === 'CONFIG') {
      		this.config = payload
      		if(!pythonStarted) {
        		pythonStarted = true;
        		this.python_start();
      		};
    	};
  	},
	stop: function() {
		const self = this;
		self.pyshell.childProcess.kill('SIGKILL');
		self.pyshell.end(function (err) {
           	if (err){
        		//throw err;
    		};
    		console.log('finished');
		});
	}
});
