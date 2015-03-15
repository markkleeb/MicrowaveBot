import time
import RPi.GPIO as GPIO
import threading, thread
from twython import TwythonStreamer, Twython
import os, urllib2


TERMS = '@MicrowaveBot2k'



GPIO.setmode(GPIO.BCM)
GPIO.setup(25, GPIO.OUT)
GPIO.output(25, GPIO.LOW)
GPIO.setup(23, GPIO.OUT)
GPIO.output(23, GPIO.LOW)
GPIO.setup(24, GPIO.OUT)
GPIO.output(24, GPIO.LOW)
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP)

connected = False

cookTime = 0
totalTime = 180
tweetTime = 0
elapsedTime = 0
stallTime = 0
userid = ''
cooking = False
stalling = False
speak = False
tweetText = ''
doorOpen = False

while (connected==False):
	try:
		stri = "https://www.google.com"
		data = urllib2.urlopen(stri)
		print "Connected"
		speak = True
		tweetText = "Connected"
		connected = True
	except:
		print "not connected"
		speak = True
		tweetText = "Cannot connect to internet"
		connected = False
		time.sleep(3)




APP_KEY = 'qKpfxH6QpxtTv3jAVFCfuuWrE'
APP_SECRET = 'oYXB7eX9VklM8WzBvrVps0nYP0vMefZok30rahYItAfmkRMJCx'
OAUTH_TOKEN = '3087471729-pOkx7VfAJYu0P41fGjn0HByUsR0v0mI26PtmGwd'
OAUTH_TOKEN_SECRET = 'vxVwsrnnUEYXHehNvKtp5Qa40fpK8tzJpWGmRHt8wFP8W'




twitter= Twython(APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)
	


class Door(threading.Thread):
	def __init__(self, threadID):
		threading.Thread.__init__(self)
		self.threadID = threadID
		self.daemon = True
	def run(self):
		global doorOpen

		while True:
			if(GPIO.input(22)==1):
				doorOpen = True
				print "Close Me!"
				time.sleep(1)
			else:
				print "Closed"
				doorOpen = False



class Timer(threading.Thread):
	def __init__(self, threadID):
		threading.Thread.__init__(self)
		self.threadID = threadID
		self.daemon = True
	def run(self):
		global cookTime
		global tweetTime
		global elapsedTime
		global totalTime
		global stallTime
		global stalling
		global cooking
		global doorOpen
		while True:
			
			if((time.time() - cookTime) > (totalTime) and cookTime != 0 and cooking == True and doorOpen ==False):
				cooking =False
				print "Done Cooking!"
				GPIO.output(24, GPIO.HIGH)
				time.sleep(0.1)
				GPIO.output(24, GPIO.LOW)
				cookTime = 0
				elapsedTime = 0
				tweetTime = 0
				try:
					twitter.update_status(status="Hey @" +userid+" Your food is done! The current time is " + time.strftime("%H:%M:%S"))
				except:
					print "Error updating status"
			elif(time.time() - tweetTime > 40 and tweetTime !=0 and cooking== True and doorOpen == False):
				cooking = False
				stalling = True
				elapsedTime = time.time() - cookTime
				stallTime = time.time()
				totalTime = totalTime - elapsedTime+ 0.5
				print "Pausing..."
				GPIO.output(23, GPIO.HIGH)
				time.sleep(0.1)
				GPIO.output(23, GPIO.LOW)
				tweetTime = 0
				try:
					twitter.update_status(status="@" +userid+" I paused your timer. There are " + str(int(totalTime)) + " seconds left to cook. The current time is " + time.strftime("%H:%M:%S"))
				except:
					print "Error updating status"
			elif(time.time() - stallTime > 20 and stalling == True and doorOpen == False):
				stallTime = time.time()
				print "stalled out"
				try:
					twitter.update_status(status="Hey @" + userid + "! Send me a tweet! Your hot pocket is getting cold! The current time is " + time.strftime("%H:%M:%S")) 
				except:
					print "error updating status"

		


class TTS(threading.Thread):
	def __init__(self, threadID):
		threading.Thread.__init__(self)
		self.threadID = threadID
		self.daemon = True
	def run(self):
		global speak
		global tweetText
		while True:

			if(speak):
				speak = False
				#tweet message, minus the user name
				tweet_msg = tweetText
			
				#text to speech using festival
				tts_command = "echo " + tweet_msg + " | festival --tts"

				#text to speech using espeak
				#tts_command = "espeak -ven+f3 -k5 -s150 " + tweet_msg

				#execute the command
				os.system(tts_command)
			


class BlinkyStreamer(TwythonStreamer):
	def on_success(self, data):
		global userid
		global cookTime
		global tweetTime
		global elapsedTime
		global totalTime
		global cooking
		global tweetText
		global speak
		global doorOpen
		global stalling

		

		if 'user' in data:
			if 'screen_name' in data['user']:
				userid = data['user']['screen_name']
		if 'text' in data:
			print data['text'].encode('utf-8')
			splitText = data['text'].split(' ', 1)[1]
			tweetText = splitText
			speak = True

			if(cookTime == 0 and tweetTime == 0 and cooking == False and doorOpen == False):
				try:
					twitter.update_status(status="Hey @" + userid + " I got your tweet at " + time.strftime("%H:%M:%S") + "! Starting to cook now for "+str(int(totalTime))+ " seconds : )")
				except:
					print "Error updating status"
				
				print "start cooking"
				cooking = True
				totalTime = 180
				cookTime = time.time()
				tweetTime = time.time()
				GPIO.output(25, GPIO.HIGH)
				time.sleep(0.1)
				GPIO.output(25, GPIO.LOW)
			elif(cookTime > 0 and tweetTime == 0 and cooking == False and doorOpen == False):
				tweetTime = time.time()
				cooking = True
				cookTime = time.time()
				stalling = False
				print "resume cooking"
				try:
					twitter.update_status(status="Okay @" +userid+" I'll start cooking again. We've got " + str(int(totalTime)) + " seconds to go. The current time is " + time.strftime("%H:%M:%S"))
				except:
					print "Error updating status"
				GPIO.output(23, GPIO.HIGH)
				time.sleep(0.1)
				GPIO.output(23, GPIO.LOW)

			elif(cookTime > 0 and tweetTime > 0 and cooking == True and doorOpen == False):
				tweetTime = time.time()
				print "added 30 seconds"
				try:
					twitter.update_status(status="Sweet @" +userid+" I'll keep on cooking! There's only " + str(int(totalTime -(time.time()-cookTime))) + " seconds left. The current time is " + time.strftime("%H:%M:%S"))
				except:
					print "Error updating status"

		


	def on_error(self, status_code, data):
		twitter.update_status(status="Hey @kleeb930 chill out for a minute - we're being blocked out! Maybe give me a reset " + time.strftime("%H:%M:%S"))
		print status_code
		print data
		GPIO.cleanup()
		stream.disconnect()




TTSThread = TTS(2)
TTSThread.start()
#doorThread = Door(3)
#doorThread.start()


if(connected):
	
	timerThread = Timer(1)
	timerThread.start()


	try:
		stream= BlinkyStreamer(APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)
		stream.statuses.filter(track=TERMS)
	
	except KeyboardInterrupt:
		cookTime = 0
		tweetTime = 0
		elapsedTime = 0
		stream.disconnect()
		GPIO.cleanup()
	


GPIO.cleanup()



	

