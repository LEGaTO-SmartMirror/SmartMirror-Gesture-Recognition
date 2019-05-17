'use strict';
const NodeHelper = require('node_helper');

const {PythonShell} = require('python-shell');
var pythonStarted = false

module.exports = NodeHelper.create({

	python_start: function () {
		const self = this;		

		
		self.pyshell = new PythonShell('modules/' + this.name + '/python-scripts/gesture_recognition.py', {pythonPath: 'python3', args: [JSON.stringify(this.config)]});
    		
		self.pyshell.on('message', function (message) {
			try{
				var parsed_message = JSON.parse(message)
           		//console.log("[MSG " + self.name + "] " + message);
				if (parsed_message.hasOwnProperty('status')){
					console.log("[" + self.name + "] " + parsed_message.status);
  				}
				if (parsed_message.hasOwnProperty('detected')){
					console.log("[" + self.name + "] detected gesture: " + parsed_message.detected.name + " center in "  + parsed_message.detected.center);
					self.sendSocketNotification('detected', JSON.stringify(parsed_message.detected));
				}
			}
			catch(err) {
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
