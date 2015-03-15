import time
import RPi.GPIO as GPIO
import threading, thread
from twython import TwythonStreamer, Twython
import os, urllib2

#search filter for twitter
TERMS = '@HotPocketBot'


#Set up pins:
# 25 = 3 minutes start
#23 = start/pause
#24 = stop/clear
#22 = door open/closed
#21 = solenoid

GPIO.setmode(GPIO.BCM)
GPIO.setup(25, GPIO.OUT)
GPIO.output(25, GPIO.LOW)
GPIO.setup(23, GPIO.OUT)
GPIO.output(23, GPIO.LOW)
GPIO.setup(24, GPIO.OUT)
GPIO.output(24, GPIO.LOW)
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(21, GPIO.OUT)
GPIO.output(21, GPIO.HIGH)

#are we connected to wifi?
connected = False

cookTime = 0
totalTime = 180
tweetTime = 0
elapsedTime = 0
stallTime = 0

#string to hold @twitter handle
userid = ''
cooking = False
stalling = False

#are we using TTS?
speak = False
tweetText = ''

#is the door open?
doorOpen = False


#check for wifi connection
while (connected==False):
	try:
		stri = "https://www.google.com"
		data = urllib2.urlopen(stri)
		print "Connected"
		tweetText = "Connected"
		speak = True
		
		connected = True
	#TTS not working here, diagnose
	except:
		print "not connected"
		tweetText = "Cannot connect to internet"
		speak = True
		connected = False
		time.sleep(3)



#Twitter credentials
APP_KEY = 'qKpfxH6QpxtTv3jAVFCfuuWrE'
APP_SECRET = 'oYXB7eX9VklM8WzBvrVps0nYP0vMefZok30rahYItAfmkRMJCx'
OAUTH_TOKEN = '3087471729-pOkx7VfAJYu0P41fGjn0HByUsR0v0mI26PtmGwd'
OAUTH_TOKEN_SECRET = 'vxVwsrnnUEYXHehNvKtp5Qa40fpK8tzJpWGmRHt8wFP8W'



#set up Twitter for sending tweets
twitter= Twython(APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)
	

#Is door open or closed?
#HIGH = Open
#LOW = closed
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



#Timers
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
		global userid
		while True:
			#Are we done cooking?
			if((time.time() - cookTime) > (totalTime) and cookTime != 0 and cooking == True and doorOpen ==False):
				cooking =False
				print "Done Cooking!"
				#send pulse on stop/clear button
				GPIO.output(24, GPIO.HIGH)
				time.sleep(0.1)
				GPIO.output(24, GPIO.LOW)
				#reset variables to zero
				cookTime = 0
				elapsedTime = 0
				tweetTime = 0
				totalTime = 180
				tweetText = userid + "please enjoy your Hot Pocket"
				speak = True
				#send tweet to user that food is done
				try:
					twitter.update_status(status="Hey @" +userid+" it's done! Now's the hard part, the 2 min cool down. Watch this to keep your hands from stuffing your face. " +  time.strftime("%H:%M:%S"))
				except:
					print "Error updating status"

			#Are we paused?
			elif(time.time() - tweetTime > 30 and tweetTime !=0 and cooking== True and doorOpen == False):
				cooking = False
				stalling = True
				#Save elapsed time to variable
				elapsedTime = time.time() - cookTime
				#Subtract from totalTime left to cook, add 0.5s for lag
				totalTime = totalTime - elapsedTime+ 0.5
				print "Pausing..."
				#Start stallTime variable
				stallTime = time.time()
				#Send pulse on start/pause button
				GPIO.output(23, GPIO.HIGH)
				time.sleep(0.1)
				GPIO.output(23, GPIO.LOW)
				tweetTime = 0
				tweetText = "no tweet no heat"
				speak = True
				#Send tweet to user that we are paused
				try:
					twitter.update_status(status="Alright @" +userid+", no tweet=no heat. There are " + str(int(totalTime)) + " seconds left to cook. " + time.strftime("%H:%M:%S"))
				except:
					print "Error updating status"

			#Are we stalling? (paused for longer than 30 seconds)
			elif(time.time() - stallTime > 30 and stalling == True and doorOpen == False):
				stallTime = time.time()
				print "pity heat"
				tweetTime = time.time()
				cookTime = time.time()
				stalling = False
				#Send tweet to user, reset StallTime
				try:
					twitter.update_status(status="You disgust me @" + userid + ", here's 30 seconds of pity heat " + time.strftime("%H:%M:%S")) 
				except:
					print "error updating status"
				#Send pulse on start/pause button
				GPIO.output(23, GPIO.HIGH)
				time.sleep(0.1)
				GPIO.output(23, GPIO.LOW)
				#Flip cooking boolean
				cooking = True

		

#TTS thread
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
			


#Twitter Stream (remains open and checking for tweets)
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

		
		#save @twitter_handle to userid variable
		if 'user' in data:
			if 'screen_name' in data['user']:
				userid = data['user']['screen_name']
		#check for text, split to remove @twitter_handle and send to TTS
		if 'text' in data:
			print data['text'].encode('utf-8')
			splitText = data['text'].split(' ', 1)[1]
			tweetText = splitText
			speak = True


			#Are we at the beginning?
			if(cookTime == 0 and tweetTime == 0 and cooking == False and doorOpen == False):
				try:
					twitter.update_status(status="Awesome @" + userid + "! Starting to cook now for "+str(int(totalTime))+ " seconds. Tweet til your Hot Pocket is hot." + time.strftime("%H:%M:%S"))
				except:
					print "Error updating status"
				
				print "start cooking"
				#set total time to 3 min
				totalTime = 180
				#reset timer variables
				cookTime = time.time()
				tweetTime = time.time()
				#send pulse to start cooking
				GPIO.output(25, GPIO.HIGH)
				time.sleep(0.1)
				GPIO.output(25, GPIO.LOW)
				#flip cooking boolean
				cooking = True
			#Are we resuming cooking after a pause?
			elif(cookTime > 0 and tweetTime == 0 and cooking == False and doorOpen == False):
				#Reset timers
				tweetTime = time.time()
				cookTime = time.time()
				stalling = False
				print "resume cooking"
				try:
					twitter.update_status(status="Okay @" +userid+" I'll start cooking again. We've got " + str(int(totalTime)) + " seconds to go. The current time is " + time.strftime("%H:%M:%S"))
				except:
					print "Error updating status"
				#Send pulse on start/pause button
				GPIO.output(23, GPIO.HIGH)
				time.sleep(0.1)
				GPIO.output(23, GPIO.LOW)
				#Flip cooking boolean
				cooking = True

			#Are we receiving a tweet while still cooking?
			elif(cookTime > 0 and tweetTime > 0 and cooking == True and doorOpen == False):
				#reset tweetTime counter
				tweetTime = time.time()
				print "added 30 seconds"
				#send tweet response
				try:
					twitter.update_status(status="Nice @" +userid+", Awesome tweets like that keep me hot. There's only " + str(int(totalTime -(time.time()-cookTime))) + " seconds left. The current time is " + time.strftime("%H:%M:%S"))
				except:
					print "Error updating status"

		

	#Twitter stream error - 420 usually
	def on_error(self, status_code, data):
		#send tweet to chill out for a bit and restart the Pi
		twitter.update_status(status="Hey @kleeb930 chill out for a minute - we're being blocked out! Maybe give me a reset " + time.strftime("%H:%M:%S"))
		print status_code
		print data
		GPIO.cleanup()
		#Following code will end program, maybe fix
		stream.disconnect()



#Start threads (not connected to wifi)
TTSThread = TTS(2)
TTSThread.start()
#doorThread = Door(3)
#doorThread.start()


if(connected):
	#Start threads (after connecting to wifi)
	timerThread = Timer(1)
	timerThread.start()
	twitter.update_status(status="I am awake and ready to tweet! Did you remember to load a hot pocket? The current time is " + time.strftime("%H:%M:%S"))

	try:
		#Connect to twitter stream, filter by TERMS
		stream= BlinkyStreamer(APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)
		stream.statuses.filter(track=TERMS)
	
	except KeyboardInterrupt:
		#Manual quit out of program
		cookTime = 0
		tweetTime = 0
		elapsedTime = 0
		stream.disconnect()
		GPIO.cleanup()
	


GPIO.cleanup()



	

