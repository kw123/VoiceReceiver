#! /Library/Frameworks/Python.framework/Versions/Current/bin/python3
# -*- coding: utf-8 -*-
####################
# voice receiver Plugin
# Developed by Karl Wachs
# karlwachs@me.com
#
#############################################################################################
#	 credit must go to  >>>> @dtich <<<  on the indigo forum who came up with the script
#	I just build the frame around it 
#############################################################################################

import datetime
import json

import subprocess
import os 
import sys
import pwd
import time
import platform
import codecs
import re

import logging
import copy

from checkIndigoPluginName import checkIndigoPluginName

_dataVersion = 1.0
_defaultName ="VoiceReceiver"
## Static parameters, not changed in pgm

_defaultDateStampFormat = "%Y-%m-%d %H:%M:%S"
_defaultDateOnlyStampFormat = "%Y-%m-%d"
_defaultTimeStampFormat = "%H:%M:%S"

# iphone sometimes sends text instead of numbers.
_mapNumbertextToInt = {"null":0, "one":1, "two":2, "three":3, "four":4, "five":5, "six":6, "seven":7, "eight":8, "nine":9, "ten":10, "eleven":11}

######### set new  pluginconfig defaults
# this needs to be updated for each new property added to pluginProps. 
# indigo ignores the defaults of new properties after first load of the plugin 
kDefaultPluginPrefs = {
	"MSG":									"please enter values",
	"expect_time_tag":						True,
	"allow_delta_time":						30.,
	"var_name":								"voice_command_text",
	"var_name_feedback":					"voice_command_feedback",
	"folder_name":							"voiceReceiver",
	"blocked_words":						"alarm|lock",
	"return_feedback":						"simple",
	## translate
	"set":									"set",
	"get":									"get",
	"to":									"to",
	"bright":								"bright",
	"level":								"level",
	"toggle":								"toggle",
	"turn":									"turn",
	"on":									"on",
	"off":									"off",
	"speed":								"speed",
	"beep":									"beep",
	"cool":									"cool",
	"heat":									"heat",
	"silence":								"silence",
	"lock":									"lock",
	"unlock":								"unlock",
	"wait":									"wait",
	"pulse":								"pulse",
	"variable":								"variable",

	"ok-set":								"set",
	"ok-get":								"",
	"ok-bright":							"brightness set",
	"ok-toggle":							"toggled",
	"ok-turn":								"turned on or off",
	"ok-speed":								"speed set",
	"ok-beep":								"beeped",
	"ok-cool":								"cool set",
	"ok-heat":								"heat set",
	"ok-silence":							"silence set",
	"ok-lock":								"locked",
	"ok-unlock":							"unlocked",
	"ok-wait":								"waited",
	"ok-pulse":								"pulsed",

	"bad-set":								"not set",
	"bad-get":								"",
	"bad-bright":							"brightness not set",
	"bad-toggle":							"not toggled",
	"bad-turn":								"not turned on or off",
	"bad-speed":							"speed not set",
	"bad-beep":								"not beeped",
	"bad-cool":								"cool not set",
	"bad-heat":								"heat not set",
	"bad-silence":							"silence not set",
	"bad-lock":								"not loked",
	"bad-unlock":							"not unlocked",
	"bad-wait":								"wait not done",
	"bad-pulse":							"not pulsed",
	

	
	"use_fragments_to_dermine_device":			False,
	"list_devices_max":							300,
	"ShowDebug":								False,
	"showLoginTest":							False,
	"debugLogic":								False,
	"debugReceiveData":							False,
	"debugBadMessage":							False,
	"debugActions":								False,
	"debugSpecial":								False,
	"debugUpdateIndigo":						False,
	"debugAll":									False
}


_debugAreas = {}
for kk in kDefaultPluginPrefs:
	if kk.find("debug") == 0:
		_debugAreas[kk.split("debug")[1]] = False


################################################################################
# noinspection PyUnresolvedReferences,PySimplifyBooleanCheck,PySimplifyBooleanCheck
class Plugin(indigo.PluginBase):
	####-----------------			  ---------
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)


###############  common for all plugins ############
		self.pluginShortName 			= _defaultName
		self.quitNOW					= ""
		self.delayedAction				= {}
		self.getInstallFolderPath		= indigo.server.getInstallFolderPath()+"/"
		self.indigoPath					= indigo.server.getInstallFolderPath()+"/"
		self.indigoRootPath 			= indigo.server.getInstallFolderPath().split("Indigo")[0]
		self.pathToPlugin 				= self.completePath(os.getcwd())

		self.pluginVersion				= pluginVersion
		self.pluginId					= pluginId
		self.pluginName					= pluginId.split(".")[-1]
		self.myPID						= os.getpid()
		self.pluginState				= "init"

		self.myPID 						= os.getpid()
		self.MACuserName				= pwd.getpwuid(os.getuid())[0]

		self.MAChome					= os.path.expanduser("~")
		self.userIndigoDir				= self.MAChome + "/indigo/"
		self.indigoPreferencesPluginDir = self.getInstallFolderPath+"Preferences/Plugins/"+self.pluginId+"/"
		self.PluginLogDir				= indigo.server.getLogsFolderPath( pluginId=self.pluginId )
		self.PluginLogFile				= indigo.server.getLogsFolderPath( pluginId=self.pluginId ) +"/plugin.log"

		formats =	{   logging.THREADDEBUG: "%(asctime)s %(msg)s",
						logging.DEBUG:       "%(asctime)s %(msg)s",
						logging.INFO:        "%(asctime)s %(msg)s",
						logging.WARNING:     "%(asctime)s %(msg)s",
						logging.ERROR:       "%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s",
						logging.CRITICAL:    "%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s"}

		date_Format = { logging.THREADDEBUG: "%Y-%m-%d %H:%M:%S",		# 5
						logging.DEBUG:       "%Y-%m-%d %H:%M:%S",		# 10
						logging.INFO:        "%Y-%m-%d %H:%M:%S",		# 20
						logging.WARNING:     "%Y-%m-%d %H:%M:%S",		# 30
						logging.ERROR:       "%Y-%m-%d %H:%M:%S",		# 40
						logging.CRITICAL:    "%Y-%m-%d %H:%M:%S"}		# 50
		formatter = LevelFormatter(fmt="%(msg)s", datefmt="%Y-%m-%d %H:%M:%S", level_fmts=formats, level_date=date_Format)

		self.plugin_file_handler.setFormatter(formatter)
		self.indiLOG = logging.getLogger("Plugin")  
		self.indiLOG.setLevel(logging.THREADDEBUG)

		self.indigo_log_handler.setLevel(logging.INFO)

		logging.getLogger("requests").setLevel(logging.WARNING)
		logging.getLogger("urllib3").setLevel(logging.WARNING)


		self.indiLOG.log(20,"initializing  ...")
		self.indiLOG.log(20,"path To files:          =================")
		self.indiLOG.log(10,"indigo                  {}".format(self.indigoRootPath))
		self.indiLOG.log(10,"installFolder           {}".format(self.indigoPath))
		self.indiLOG.log(10,"plugin.py               {}".format(self.pathToPlugin))
		self.indiLOG.log(10,"indigo                  {}".format(self.indigoRootPath))
		self.indiLOG.log(20,"detailed logging in     {}".format(self.PluginLogFile))
		if self.pluginPrefs.get('showLoginTest', True):
			self.indiLOG.log(20,"testing logging levels, for info only: ")
			self.indiLOG.log( 0, "logger  enabled for     0 ==> TEST ONLY ")
			self.indiLOG.log( 5, "logger  enabled for     THREADDEBUG    ==> TEST ONLY ")
			self.indiLOG.log(10, "logger  enabled for     DEBUG          ==> TEST ONLY ")
			self.indiLOG.log(20, "logger  enabled for     INFO           ==> TEST ONLY ")
			self.indiLOG.log(30, "logger  enabled for     WARNING        ==> TEST ONLY ")
			self.indiLOG.log(40, "logger  enabled for     ERROR          ==> TEST ONLY ")
			self.indiLOG.log(50, "logger  enabled for     CRITICAL       ==> TEST ONLY ")
			self.indiLOG.log(10, "Plugin short Name       {}".format(self.pluginShortName))
		self.indiLOG.log(10, "my PID                  {}".format(self.myPID))
		self.indiLOG.log(10, "Achitecture             {}".format(platform.platform()))
		self.indiLOG.log(10, "OS                      {}".format(platform.mac_ver()[0]))
		self.indiLOG.log(10, "indigo V                {}".format(indigo.server.version))
		self.indiLOG.log(10, "python V                {}.{}.{}".format(sys.version_info[0], sys.version_info[1] , sys.version_info[2]))
		self.epoch = datetime.datetime(1970, 1, 1)

		self.restartPlugin = ""

		self.pythonPath = ""
		if os.path.isfile("/Library/Frameworks/Python.framework/Versions/Current/bin/python3"):
				self.pythonPath				= "/Library/Frameworks/Python.framework/Versions/Current/bin/python3"
		self.indiLOG.log(20,"using '{}' for utily programs".format(self.pythonPath))

###############  END common for all plugins ############
		#self.sleep(0)
		return


	####-----------------			  ---------
	def __del__(self):
		indigo.PluginBase.__del__(self)

	###########################		INIT	## START ########################

	####----------------- @ startup set global parameters, create directories etc ---------
	def startup(self):

		self.quitNOW = ""

		if not checkIndigoPluginName(self, indigo):
			exit()
			
		self.pluginStartTime = time.time()
		self.redoInitVariables = True
		self.setDebugFromPrefs(self.pluginPrefs, writeToLog=False)
		
		return


	####-----------------	 ---------
	def initVariables(self):
		try:
			self.redoInitVariables = False

			if not os.path.exists(self.indigoPreferencesPluginDir):
				os.mkdir(self.indigoPreferencesPluginDir)
			if not os.path.exists(self.indigoPreferencesPluginDir):
				self.indiLOG.log(50,"error creating the plugin data dir did not work, can not create: {}".format(self.indigoPreferencesPluginDir)  )
				self.sleep(1000)
				exit()
				
			self.translate = {}
			for xx in ["set", "get", "to", "level", "bright", "toggle", "pulse", "turn", "on", "off", "speed", "beep", "cool", "heat", "lock", "unlock", "silence", "variable", "wait"]:
				self.translate[xx] = self.pluginPrefs.get(xx, kDefaultPluginPrefs[xx])

			self.feedback_ok = {}
			for xx in ["set", "get", "bright", "toggle", "pulse", "turn", "speed", "beep", "cool", "heat", "lock", "unlock", "silence", "wait"]:
				self.feedback_ok[xx] = self.pluginPrefs.get("ok-"+xx, kDefaultPluginPrefs["ok-"+xx])

			self.feedback_bad = {}
			for xx in ["set", "get", "bright", "toggle", "pulse", "turn", "speed", "beep", "cool", "heat", "lock", "unlock", "silence", "wait"]:
				self.feedback_bad[xx] = self.pluginPrefs.get("bad-"+xx, kDefaultPluginPrefs["bad-"+xx])
	
			self.synonymes_for_actions    = self.readJson(self.indigoPreferencesPluginDir+"synonymes_for_actions.json", defReturn={})
			self.synonymes_for_devices    = self.readJson(self.indigoPreferencesPluginDir+"synonymes_for_devices.json", defReturn={})
			self.synonymes_for_variables  = self.readJson(self.indigoPreferencesPluginDir+"synonymes_for_variables.json", defReturn={})

			self.map_from_to = {
					"the block": "debug",
					"hieu": "hue",
					"hugh": "hue",
			}

			test  = self.readJson(self.indigoPreferencesPluginDir+"map_from_to.json", defReturn={})
			if test != {}:
				self.map_from_to  = test

			self.blocked_words= self.pluginPrefs.get("blocked_words", kDefaultPluginPrefs["blocked_words"]).split("|")

			test = self.readJson(self.indigoPreferencesPluginDir+"blocked_words.json", defReturn={})
			if test != {}:
				self.blocked_words= test

			test = self.readJson(self.indigoPreferencesPluginDir+"failed_commands.json", defReturn={})
			if test != {}:
				self.failed_commands = test
			else:
				self.failed_commands = {}
			test = self.readJson(self.indigoPreferencesPluginDir+"ok_commands.json", defReturn={})
			if test != {}:
				self.ok_commands = test
			else:
				self.ok_commands = {}

			self.use_fragments_to_dermine_device = self.pluginPrefs.get("use_fragments_to_dermine_device", kDefaultPluginPrefs["use_fragments_to_dermine_device"])

			self.allow_delta_time = float(self.pluginPrefs.get("allow_delta_time", kDefaultPluginPrefs["allow_delta_time"]*10.))/10.
			self.expect_time_tag = self.pluginPrefs.get("expect_time_tag", kDefaultPluginPrefs["expect_time_tag"])

			self.list_devices_max = self.pluginPrefs.get("list_devices_max", kDefaultPluginPrefs["list_devices_max"])

			self.folder_name = self.pluginPrefs.get("folder_name", kDefaultPluginPrefs["folder_name"])	
			try:    indigo.variables.folder.create(self.folder_name)
			except: pass

			self.var_name = self.pluginPrefs.get("var_name", kDefaultPluginPrefs["var_name"])	
			try:    indigo.variable.create(self.var_name,  "", self.folder_name)
			except: pass

			self.return_feedback = self.pluginPrefs.get("return_feedback", kDefaultPluginPrefs["return_feedback"])	
			
	
			self.var_name_feedback = self.pluginPrefs.get("var_name_feedback", kDefaultPluginPrefs["var_name_feedback"])	
			try:    indigo.variable.create(self.var_name_feedback,  "", self.folder_name)
			except: pass
			
			
			self.setDebugFromPrefs(self.pluginPrefs)
			self.actionNumber = 0
			self.actionId = 0

		except	Exception as e:
				if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)


	####-----------------  ---------
	def getMenuActionConfigUiValues(self, menuId: str) -> dict:
		xx =  super(Plugin, self).getMenuActionConfigUiValues(menuId)
		if menuId == "blockedWords":
			yy = ("|").join(self.blocked_words)
			xx[0]["blocked_words"] = yy
		return xx
		
	####-----------------  ---------
	#### good bad words 
	####-----------------  ---------
	def blockWordsCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20, f"blockWordsCallback {valuesDict}")
		yy = valuesDict["blocked_words"].split("|")
		self.blocked_words= []
		for xx in yy:
			if xx.strip() != "":
				self.blocked_words.append(xx.strip())
		self.writeJson(self.blocked_words, fName=self.indigoPreferencesPluginDir + "blocked_words.json", sort = True, doFormat=True, singleLines= False )



	def filterFromTo(self, filter="", valuesDict=None , typeId=None):
		xList = []
	
		for syn in self.map_from_to:
			xList.append([syn, syn+"->"+self.map_from_to[syn]])
		#self.indiLOG.log(20, f"filterSynonymes xList: {xList}")
		return xList


	####-----------------  ---------
	def addFromCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20, f"selectActionsCallback {valuesDict}")
		bad = valuesDict["from"]
		good = valuesDict["to"]
		if bad not in self.map_from_to:
			self.map_from_to[bad] = good
		self.writeJson(self.map_from_to, fName=self.indigoPreferencesPluginDir + "map_from_to.json", sort = True, doFormat=True, singleLines= False )


	####-----------------  ---------
	def removeFromCallback(self, valuesDict=None , typeId=""):
		bad = valuesDict["fromRemove"]
		if bad in self.map_from_to:
			del self.map_from_to[bad]
		self.indiLOG.log(20, f"removeFromCallback {bad}  {self.map_from_to}")
		self.writeJson(self.map_from_to, fName=self.indigoPreferencesPluginDir + "map_from_to.json", sort = True, doFormat=True, singleLines= False )


	####-----------------  ---------
	#### define synonymes for actions
	####-----------------  ---------
	def filterActions(self, filter="", valuesDict=None , typeId=None):
		# also used to enable and disable actions 
		xList = []
		if filter  == "synonymes":
			for action in indigo.actionGroups.iter(self.pluginId):
				xList.append([action.id, action.name])

		#self.indiLOG.log(20, f"filterActions xList: {xList}")
		return xList


####-------------------------------------------------------------------------####
	def filterSynonymesActions(self, filter="", valuesDict=None , typeId=None):
		xList = []
	
		for syn in self.synonymes_for_actions:
			xList.append([syn, syn])
		#self.indiLOG.log(20, f"filterSynonymes xList: {xList}")
		return xList


	def addSynonymActionCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20, f"selectActionsCallback {valuesDict}")
		id = valuesDict["id"]
		synonym = valuesDict["add"]
		if synonym not in self.synonymes_for_actions:
			self.synonymes_for_actions[synonym] = id
		self.writeJson(self.synonymes_for_actions, fName=self.indigoPreferencesPluginDir + "synonymes_for_actions.json", sort = True, doFormat=True, singleLines= False )


	####-----------------  ---------
	def removeSynonymActionCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20, f"selectActionsCallback {valuesDict}")
		synonym = valuesDict["remove"]
		if synonym in self.synonymes_for_actions:
			del self.synonymes_for_actions[synonym]
		self.writeJson(self.synonymes_for_actions, fName=self.indigoPreferencesPluginDir + "synonymes_for_actions.json", sort = True, doFormat=True, singleLines= False )


	####-----------------  ---------
	#### define synonymes for devices
	####-----------------  ---------
	def filterDevices(self, filter="", valuesDict=None , typeId=None):
		# also used to enable and disable actions 
		xList = []
	
		for dev in indigo.devices.iter():
			xList.append([dev.id, dev.name])
			continue
							
		#self.indiLOG.log(20, f"filterActions xList: {xList}")
		return xList


	def filterSynonymesDevices(self, filter="", valuesDict=None , typeId=None):
		xList = []
		for syn in self.synonymes_for_devices:
			xList.append([syn, syn])
		#self.indiLOG.log(20, f"filterSynonymes xList: {xList}")
		return xList


	def addSynonymDeviceCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20, f"selectActionsCallback {valuesDict}")
		id = valuesDict["id"]
		synonym = valuesDict["add"]
		if synonym not in self.synonymes_for_devices:
			self.synonymes_for_devices[synonym] = id
		self.writeJson(self.synonymes_for_devices, fName=self.indigoPreferencesPluginDir + "synonymes_for_devices.json", sort = True, doFormat=True, singleLines= False )


	####-----------------  ---------
	def removeSynonymDeviceCallback(self, valuesDict=None , typeId=""):
		s#elf.indiLOG.log(20, f"selectActionsCallback {valuesDict}")
		synonym = valuesDict["remove"]
		if synonym in self.synonymes_for_devices:
			del self.synonymes_for_devices[synonym]
		self.writeJson(self.synonymes_for_devices, fName=self.indigoPreferencesPluginDir + "synonymes_for_devices.json", sort = True, doFormat=True, singleLines= False )


	####-----------------  ---------
	#### define synonymes for variables
	####-----------------  ---------
	def filterVariables(self, filter="", valuesDict=None , typeId=None):
		# also used to enable and disable actions 
		xList = []
	
		for var in indigo.variables.iter():
			xList.append([var.id, var.name])
			continue
							
		#self.indiLOG.log(20, f"filterActions xList: {xList}")
		return xList


	def filterSynonymesVariables(self, filter="", valuesDict=None , typeId=None):
		xList = []
	
		for syn in self.synonymes_for_variables:
			xList.append([syn, syn])
		#self.indiLOG.log(20, f"filterSynonymes xList: {xList}")
		return xList


	def addSynonymVariableCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20, f"selectActionsCallback {valuesDict}")
		id = valuesDict["id"]
		synonym = valuesDict["add"]
		if synonym not in self.synonymes_for_variables:
			self.synonymes_for_variables[synonym] = id
		self.writeJson(self.synonymes_for_variables, fName=self.indigoPreferencesPluginDir + "synonymes_for_variables.json", sort = True, doFormat=True, singleLines= False )


	####-----------------  ---------
	def removeSynonymVariableCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20, f"selectActionsCallback {valuesDict}")
		synonym = valuesDict["remove"]
		if synonym in self.synonymes_for_variables:
			del self.synonymes_for_variables[synonym]
		self.writeJson(self.synonymes_for_variables, fName=self.indigoPreferencesPluginDir + "synonymes_for_variables.json", sort = True, doFormat=True, singleLines= False )


####-------------------------------------------------------------------------####
	def filternumbers_1_100(self, filter="", valuesDict=None , typeId=None):
		xList = []
	
		for ii in range(1,100):
			xList.append([ii, ii])
		return xList


	####-----------------	 ---------
	def printHelp(self,  valuesDict=None , typeId=""):
		try:
			out =  '\n'
			out += '\n'
			out += 'HELP =====================\n'
			out += '#########################################################################\n'
			out += ' credit must go to @dtich on the indigo forum who came up with the script\n'
			out += '#########################################################################\n'
			out += '\n'
			out += 'What does it do?\n'
			out += '  the PLUGIN \n'
			out += '  - receives message in indigo variable from iphone dictation shortcut \n'
			out += '  - analyses the received string to look for commands to \n'
			out += '    --   start indigo actions (must be defined in plugin menu)\n'
			out += '    --   switch on/off or dim devices set variables,  etc\n'
			out += '  - sends back  ok / not sucessful (you can set) and the iphone speaks that text\n'
			out += '  - in menu you can define / do :\n'
			out += '    1. synonymes for devices, variables, actions \n'
			out += '    2. mappings of bad to good words (eg "hugh" to "hue" or "the bug" to "debug") the plugin will replace the bad strings with the good\n'
			out += '    3. block words eg if "alarm" is set as blocked word any command containing "alarm" will be ignored\n'
			out += '    4. print help / config and stats ( how often and when was a command received) to logfile\n'
			out += '\n'
			out += '  the SHORTCUT on the iphone / mac / ipad /..  \n'
			out += '  - listens to commands or has a command hardwired into code \n'
			out += '  - sends command into indigo variable  ".. command .." \n'
			out += '  - receives result from variable ".. feedback .." \n'
			out += '  - speaks result  (ok  / not successful) depening on settings\n'
			out += '\n'
			out += '================================ INSTALL ===========================\n'
			out += '\n'
			out += '(A) After plugin install define the configurations in plugin config and menu, see below\n'
			out += '  in config define \n'
			out += '    variable and folder names\n'
			out += '    (language) mappings for on/off turn .. to other languages if you like\n'
			out += '     eg on -> an   or   set --> write\n'
			out += '  in menu define\n'
			out += '    - synonymes for actions, devices, variables: \n'
			out += '          to be used: eg use "open garage" instead of "garage door open relay" \n'
			out += '    - mappings of bad to good words:  eg "hugh" to "hue" or "the bug" to "debug";  the plugin will replace the bad strings with the good\n'
			out += '    - block words: eg if "alarm" is set as blocked word any command containing "alarm" will be ignored\n'
			out += '\n'
			out += '(B) === Create shortcut on iPhone with the following items: ====\n'
			out += '  you can download a shortcut with empty keys etc at https://www.icloud.com/shortcuts/4ae22c3cfefc4861a627daa6afff3551\n'
			out += '   then replace\n'
			out += '  - <your id>  = your indigo domo userid;\n'
			out += '  - <indigo variable id command> this is the indigo command variable id #where the plugin received the comamnds\n'
			out += '  - "<indigo variable id feedback> this is the indigo variable id # that contains the feedback to the iphone \n'
			out += '  - "192.168.1." with the first part of your local ip numbers, or your complete iPhone home ip number if it is fixed at home \n'
			out += '  - <your key>  get it at https://www.indigodomo.com/account/authorizations\n'
			out += '\n'
			out += '= ==== manual creation if you want to do that:\n'
			out += '   set comamnds                                                      comments / explanations \n'
			out += '1. Text xxx or command you want to issue                             enter command or xxx to use "dictate"\n'
			out += '                                                                     use here eg "turn on deviceid:12345" to use as hardwired shortcut ommand\n'
			out += '                                                                     use here  xxx" then the shortcut shall listen to your commands\n'
			out += '2. set variable command to Text                                      copy above value to variable "command" \n'
			out += '3. if command is xxx                                                 do we have a command or should we do dictate?\n'
			out += '3.1 Dismiss Siri and Continue                                        to shorten pause \n'
			out += '3.2 Dictate text                                                     this is where the voice gets recorded\n'
			out += '3.3 set variable command to Dictated text                            copy dictated text to variable "command" \n'
			out += '3. end if                                                            command is now in variable command either from first line or dictate\n'
			out += '4. Current Date                                                      create date object  \n'
			out += '5. Get Seconds between 1970-01-01 0:00 z and Date                    create time since epoch in secs  \n'
			out += '6. Text "Time Between Dates"  variable command                       create text string to be send: timestamp space command\n'
			out += '7. get current IP Address (local)                                    \n'
			out += '8. if Current IP Address contains 192.168.1.                         if local (your iphone ip): use your local indigo ip number\n'
			out += '8.1. Get contents of https://ip of indigo server:8176/v2/api/command for local indigo contact  \n'
			out += '8.1.1   method Post\n'
			out += '8.1.1.1    Headers\n'
			out += '8.1.1.2    Authorization  Bearer <your key>                           from indigo web page \n'
			out += '8.1.1.3    Content-Type applicatio/json\n'
			out += '8.1.1.4    Request Body: JSON\n'
			out += '8.1.1.4.1    message : Text indigovariable.updateValue\n'
			out += '8.1.1.4.2    objectId : <indigo variable id command>                 here you put the indigo variable id\n'
			out += '8.1.1.4.3    parameters : Dictionary\n'
			out += '8.1.1.4.3.1    value  Text: Text                                     this is the varibale that contains time space command\n'
			out += '8.1.2. Get contents of http://ip of indigo server:8176/v2/api/variable/<indigo variable id feedback>     \n'
			out += '8.1.2.1   method get\n'
			out += '8.1.2.2   Headers\n'
			out += '8.1.2.2.1    Authorization  Bearer <your key>                        from indigo web page \n'
			out += '8.1.2.3.2    Content-Type applicatio/json\n'
			out += '8.1.3  get value for value in get contents of URL\n'
			out += '8.1.4  speak Dictionary value                                        this will speak the reslt send back from the plugin ok/ bad\n'
			out += '8.2. Otherwise \n'
			out += '8.2. Get contents of https://<your id>indigodome.net/v2/api/command   not local indigo exernal contact  \n'
			out += '8.2.1.   method Post\n'
			out += '8.2.1.1.   Headers\n'
			out += '8.2.1.2    Authorization  Bearer <your key>                          from indigo web page \n'
			out += '8.2.1.3    Content-Type applicatio/json\n'
			out += '8.2.1.4    Request Body: JSON\n'
			out += '8.2.1.4.1    message : Text indigovariable.updateValue\n'
			out += '8.2.1.4.2    objectId : <indigo variable id command>                  here you put the indigo variable id\n'
			out += '8.2.1.4.3    parameters : Dictionary\n'
			out += '8.2.1.4.3.1  value  Text: Text                                        this is the varibale that contains result text\n'
			out += '8.2.2 Get contents of https://<your id>indigodomo.net/v2/api/variable/<indigo variable id feedback>     \n'
			out += '8.2.2.1   method get\n'
			out += '8.2.2.2   Headers\n'
			out += '8.2.2.2.1    Authorization  Bearer <your key>                         from indigo web page \n'
			out += '8.2.2.2.2    Content-Type applicatio/json\n'
			out += '8.2.3  get value for value in get contents of URL\n'
			out += '8.2.4  speak Dictionary value                                         this will speak the reslt send back from the plugin ok/ bad\n'
			out += '\n'
			out += '9. name it eg "indigo" \n'
			out += '10. share to desktop as eg indigo\n'
			out += '\n'
			out += '=== END create shortcut  ...  ====\n'
			out += '\n'
			out += 'speaking "hey Siri Indigo" pause "turn on office lights"  \n'
			out += '    you could also define eg "hey indigo do" as hey siri replacement for this shortcut:   \n'
			out += '     settings / Accessibility  / vocal short cuts / add action / select yor shorcut say "hey indigo do" 3 times  save  \n'
			out += 'if you have a light named office lights:  \n'
			out += '     "hey indigo do"  pause  "turn on office lights"  should turn on your office lights    \n'
			out += '\n'
			out += '\n'
			out += '====  commands ====================================================\n'
			out += '   substitute <device> with device name or synonym or deviceid:<devId>:  \n'
			out += '   substitute <variable> with variable name or synonym  or variableid:<varId>: \n'
			out += '   substitute <action> with action synonym  or actionid:<vactionId>: \n'
			out += '   substitute <state> with state name  \n'
			out += '   substitute <value> with  value to be used \n'
			out += '   upper and lower cases are ignored\n'
			out += '   To make find dev anmes etc easier : \n'
			out += '     commands  and names received will be "normalized:" \n'
			out += '        "_"  and "-" "?" "."  will be replaced by " " \n'
			out += '     indigo device and variable names and state names will be normalized:" \n'
			out += '        "abcDef"  will be replaced by "abc def"  \n'
			out += '        "_"  and "-"  will be replaced by " " \n'
			out += '   then incoming and indigo names etc can be better compared\n'
			out += '   the execution is checked in the listed sequence to make sure that they are not ambigous\n'
			out += '   \n'
			out += '   set variable <variable> to value                                  write value to variable\n'
			out += '   get variable <variable>                                           get var value and speak it\n'
			out += '   get <device> state <state>                                        get dev/state value and speak it\n'
			out += '                                                                     notice the differnce to get variable \n'
			out += '   speed <device> to xx                                              for fans; (0-4 or 100)  one, two mapped to 1, 2\n'
			out += '   beep <device>  \n'
			out += '   lock <device>  \n'
			out += '   unlock <device>  \n'
			out += '   turn on/off <device>                                              \n'
			out += '   toggle <device>                                                   \n'
			out += '   pulse <device> <secs>                                             on for xx secs then off, default = 1 secs     \n'
			out += '   (set) heat <device> to <degrees>                                  for thermostates to set heat target temp \n'
			out += '   (set) cool <device> to <degrees>                                  for thermostatesto seth ac target temp\n'
			out += '   (set) bright(ness level) <device> (to) <value> (percent / %)      will set brightess of dimmer device to <value> 0..100  \n'
			out += '   "and"  or  "&""  or  "then"                                       can be used to concatenate several commands"\n'
			out += '\n'
			out += '=== meta commands ==================================================\n'
			out += '  list devices                                                       will print xx # of devices to logfile;  just to show \n'
			out += '  debug on                                                           will enable debug all \n'
			out += '  debug off                                                          will disable debug all \n'
			out += '  test                                                               will print "test" to logfile \n'
			out += '  help                                                               will print ALL THIS to logfile \n'
			out += '\n'
			out += '\n'
			out += 'Examples for commands:\n'
			out += '   turn on office lights                                             will turn on office lights and the phone will speak "ok" or "turned on" depending on settings \n'
			out += '   turn on deviceid:12345:                                           will turn on indigo device with id 12345 \n'
			out += '   toggle deviceid:12345:                                            will toggle indigo device with id 12345 \n'
			out += '   pulse deviceid:12345: 5 sec                                       will turn on indigo device with id 12345 for 5 secs then off\n'
			out += '   open garage                                                       will be execute taht action if you have defined "open garage" as a synonym for an action\n'
			out += '   actionid:54321                                                    will execute indigo action with id 54321 if it exists\n'
			out += '   bright <device1> to xx and wait 5 and  turn on <device2>          will execute 3 commands  \n'
			out += '   turn on ;SKD;ASJ  on                                              will fail and the iphone will speak "not executed" or "device not found" depending on settings \n'
			out += '\n'
			out += '\n'

			self.indiLOG.log(20,out)
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return


	####-----------------	 ---------
	def printConfig(self,  valuesDict=None , typeId=""):
		try:
			out = '\n'
			out += '\n'
			out += 'Plugin config Parameters ===========\n'
			out += f'allow_delta_time        = {self.allow_delta_time}\n'
			out += '                           message must not be older thn current timestamp +  allow_delta_time\n\n'
			out += f'expect_time_tag         = {self.expect_time_tag}\n'
			out += '                           require time stamp value as first work in message\n\n'
			out += f'use fragments           = {self.use_fragments_to_dermine_device}\n'
			out += '                           allow plugin to try to figure out which device was mean if not 100 % match using fragments\n\n'
			out += f'var_name                = {self.var_name}\n'
			out += '                           name of the variable the plugin will listen to, will be created if it does not exist\n\n'
			out += f'var_name_feedback       = {self.var_name_feedback}\n'
			out += '                           name of the variable the plugin will write result to be pickup by iphone, will be created if it does not exist\n\n'
			out += f'return feedback          = {self.return_feedback}\n'
			out += '                           return what to iphone  "blank" or "ok/not executed" or detailed info\n\n'
			out += f'return if successful    = {self.feedback_ok}\n'
			out += '                           return strings if sucessful\n\n'
			out += f'return if failed        = {self.feedback_bad}\n'
			out += '                           return strings if not sucessful\n\n'
			out += f'folder_name             = {self.folder_name}\n'
			out += '                           folder name of the variables, will be created if it does not exist\n\n'
			out += f'blocked_words           = {self.blocked_words}\n'
			out += '                           words that are not allowed for devices and actions eg "alarm", when they are present the whole command is ignored\n\n'
			xx = ""
			for syn in self.synonymes_for_actions:
				devId = int(self.synonymes_for_actions[syn])
				xx+= f'{syn}: id {devId} = {indigo.actionGroups[devId].name}; '
			out += f'synonymes for actions   = {xx}\n'
			out += '                           voice action phrase: indigo action ids, indigo name  \n\n'
			xx = ""
			for syn in self.synonymes_for_devices:
				devId = int(self.synonymes_for_devices[syn])
				xx+= f'{syn}: id {devId} = {indigo.devices[devId].name}; '
			out += f'synonymes for devices   = {xx}\n'
			out += '                           voice device phrase: indigo device ids, uindigo name   \n\n'
			xx =""
			for syn in self.synonymes_for_variables:
				devId = int(self.synonymes_for_variables[syn])
				xx+= f'{syn}: id {devId} = {indigo.variables[devId].name}; '
			out += f'synonymes for variables = {xx}\n'
			out += '                           voice variable phrase: indigo variable ids, indigo name  \n\n'
			out += f'map_from_to             = {self.map_from_to}\n'
			out += '                           bad phrases to be replaced by good phrases  using {map voice string : to string to be used} \n\n'
			out += '                           eg the bug -> debug  \n\n'
			out += '                           eg dor     -> door  \n\n'
			out += '                           or tür     -> door (for the germans)  \n\n'
			out += f'list devices max        = {self.list_devices_max}\n'
			out += '                           list max number of devices when receiving command list devices \n\n'

			self.indiLOG.log(20,out)
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return


	def printStats(self, valuesDict=None, id=None):
		try:
			out = '\n'
			out += '\n'
			out += '====================== STATS ==================================\n'
			out += '\n'
			out += 'FAILED commands                            count date,      date,      ===========================================================\n'
			for xx in self.failed_commands:
				theDates = (", ").join(self.failed_commands[xx])
				nn = len(self.failed_commands[xx])
				out += f'{xx.strip():45}{nn:3} {theDates} \n'
			out += '\n\n'
			out += 'OK commands                                count date,      date,      ===========================================================\n'
			for good in self.ok_commands:
				theDates = (", ").join(self.ok_commands[good])
				nn = len(self.ok_commands[good])
				out += f'{good.strip():45}{nn:3} {theDates} \n'
			out += '\n'
			out += '====================== STATS END ==============================\n'
			self.indiLOG.log(20,out)
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return


	####-----------------	 ---------
	def resetStats(self, valuesDict=None, id=None):
		self.failed_commands = dict()
		self.ok_commands = dict()
		self.writeJson(self.failed_commands, fName=self.indigoPreferencesPluginDir + "failed_commands.json", verbose=False)
		self.writeJson(self.ok_commands, fName=self.indigoPreferencesPluginDir + "ok_commands.json", verbose=False)
		valuesDict ["MSG"] = "stats resetted"
		return valuesDict


	####-----------------	 ---------
	def setDebugFromPrefs(self, theDict: dict, writeToLog=True):
		self.debugAreas = []
		try:
			for d in _debugAreas:
				if theDict.get("debug"+d, False): self.debugAreas.append(d)
			if writeToLog: self.indiLOG.log(20, "debug areas: {} ".format(self.debugAreas))
		except	Exception as e:
				if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)


	####-----------------	 ---------
	def completePath(self, inPath:str):
		if len(inPath) == 0: return ""
		if inPath == " ":	 return ""
		if inPath[-1] !="/": inPath +="/"
		return inPath


	####-------------------------------------------------------------------------####
	def readJson(self, fName:str, defReturn={}):
		try:
			if os.path.isfile(fName):
				f = self.openEncoding(fName,"r")
				data = json.loads(f.read())
				f.close()
				return data
			else:
				#self.indiLOG.log(20,"readJson does not exist fName:{} ".format(fName))
				return defReturn
				
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
			self.indiLOG.log(20,"readJson error for fName:{} ".format(fName))
		return defReturn


	####-------------------------------------------------------------------------####
	def writeJson(self, data: dict, fName="", sort=True , doFormat=True, singleLines=False, verbose= False):
		try:
			out = ""
			if doFormat:
				if singleLines:
					out = ""
					for xx in data:
						out += "\n{}:{}".format(xx, data[xx])
					out = out.strip()
				else:
					try: out = json.dumps(data, sort_keys=sort, indent=2)
					except: pass
			else:
					try: out = json.dumps(data, sort_keys=sort)
					except: pass

			if fName != "":
				if verbose:
					self.indiLOG.log(20,"writeJson  out=\n{} ".format(out))
				f = self.openEncoding(fName,"w")
				f.write(out)
				f.close()

			if data == "": return ""
			if data == {} : return ""
			if data is None: return ""
			return out

		except	Exception as e:
			self.indiLOG.log(40,"", exc_info=True)
			self.indiLOG.log(20,"writeJson error for fname:{} ".format(fName))
		return ""


	####-------------------------------------------------------------------------####
	def readPopen(self, cmd: str):
		try:
			ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			return ret.decode('utf-8'), err.decode('utf-8')

		except Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)


	####-------------------------------------------------------------------------####
	def openEncoding(self, fName: str , readOrWrite: str):

		try:
			if readOrWrite.find("b") > -1:
				return open( fName, readOrWrite)

			if sys.version_info[0]  > 2:
				return open( fName, readOrWrite, encoding="utf-8")

			else:
				return codecs.open( fName, readOrWrite, "utf-8")

		except	Exception as e:
			self.indiLOG.log(20,"openEncoding error w r/w:{}, fname:".format(readOrWrite, fName))
			self.indiLOG.log(40,"", exc_info=True)


	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called once the user has exited the preferences dialog
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	####-----------------  set the geneeral config parameters---------
	def validatePrefsConfigUi(self, valuesDict: dict):

		errorDict = indigo.Dict()
		try:
			valuesDict["MSG"]					= "ok"
			self.allow_delta_time =				float(valuesDict.get("allow_delta_time", self.allow_delta_time)*10.)/10.
			self.expect_time_tag =				valuesDict.get("expect_time_tag", self.expect_time_tag)
			self.folder_name =					valuesDict.get("folder_name", self.folder_name)
			self.var_name =						valuesDict.get("var_name", self.var_name)
			self.var_name_feedback =			valuesDict.get("var_name_feedback", self.var_name_feedback)

			self.redoInitVariables = 		True
			return True, valuesDict

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return False, errorDict, valuesDict

	###########################		Prefs	## END ############################


	###########################	              ############################
	###########################	   MAIN LOOP  ############################
	###########################	              ############################

	####-----------------init  main loop ---------
	def fixBeforeRunConcurrentThread(self) -> bool:

		nowDT = datetime.datetime.now()
		self.lastMinute		= nowDT.minute
		self.lastHour		= nowDT.hour
		self.writeJson({"version":_dataVersion}, fName=self.indigoPreferencesPluginDir + "dataVersion")
		self.initVariables()
		indigo.variables.subscribeToChanges()
		return True


	####-----------------   main loop          ---------
	def runConcurrentThread(self):

		if not self.fixBeforeRunConcurrentThread():
			self.indiLOG.log(40,"..error in startup")
			self.sleep(100)
			return

		self.indiLOG.log(20,"runConcurrentThread.....")

		try:
			while True:
				self.sleep(1)
				if self.redoInitVariables:
					self.initVariables()
					
				if self.quitNOW != "": 
					break
	 
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		self.indiLOG.log(20,"after loop , quitNow= >>{}<<".format(self.quitNOW ) )

		indigo.server.savePluginPrefs()	

		self.sleep(1)
		if self.quitNOW !="":
			self.indiLOG.log(20, "runConcurrentThread stopping plugin due to:  ::::: {} :::::".format(self.quitNOW))
			serverPlugin = indigo.server.getPlugin(self.pluginId)
			serverPlugin.restart(waitUntilDone=False)
		return


	###########################	                      ############################
	###########################	receive text and act   ############################
	###########################	                       ############################

	def variableUpdated(self, orig_var: dict, new_var: dict ):
		if self.var_name != orig_var.name: return 
		self.finished = False
		self.foundCommand = False
		indigo.variable.updateValue(self.var_name_feedback, value=" ")
		self.variableUpdated_action(new_var.value)
		if self.return_feedback == "off":
				 				indigo.variable.updateValue(self.var_name_feedback, value=" ")
		else:
			if self.finished:	indigo.variable.updateValue(self.var_name_feedback, value=self.feedback_value)
			else: 				indigo.variable.updateValue(self.var_name_feedback, value="not finshed")
		
		return  


	def variableUpdated_action(self, new_var:str ):
		try:
			if self.decideMyLog("ReceivdeData"): self.indiLOG.log(20, f'var changed  "{new_var}"')
				
			self.raw = new_var
	
			#if self.decideMyLog("ReceivdeData"): self.indiLOG.log(20, f"Command received raw: '{self.raw}'")
	
			if not self.raw or not self.raw.strip():
				return
	

			ok, raw_stripped = self.check_if_time_tag_ok(self.raw.strip())
			if not ok: 
				return 
	
			if self.decideMyLog("ReceiveData"): self.indiLOG.log(20, f"Command received raw, tags removed: '{raw_stripped}'")
	
			# replace _- A -> a string, remove double spaces etc 
			cmd =  self.normalize_command(raw_stripped)
			
			if self.decideMyLog("ReceiveData"): self.indiLOG.log(20, f"Normalized command: '{raw_stripped}'")
	
			########## simple commands  #######
	
			if cmd == "list devices":
				self.log_devices()
				self.stats_good(True, "devices printed")
				return
	
			elif cmd == "test":
				self.indiLOG.log(20, f"received command: '{raw_stripped}'")
				self.stats_good(True, "test received")
				return
	
			elif cmd == "debug on":
				self.indiLOG.log(20, f"received command: '{raw_stripped}'")
				self.pluginPrefs["debugAll"] = True
				self.setDebugFromPrefs(self.pluginPrefs)
				self.stats_good(True, "debug on")
				return

			elif cmd == "debug off":
				self.indiLOG.log(20, f"received command: '{raw_stripped}'")
				self.pluginPrefs["debugAll"] = False
				self.stats_good(True, "debug off")
				self.setDebugFromPrefs(self.pluginPrefs)

			elif cmd == "help":
				self.indiLOG.log(20, f"received command: '{raw_stripped}'")
				self.printHelp()
				self.printConfig()
				self.printStats()
				self.stats_good(True, "help printed")
				return

			elif cmd.find(self.translate["silence"]) >-1:
				self.indiLOG.log(20, f"received command: '{raw_stripped}'")
				if cmdLower.find(" "+self.translate["on"]) > 5:
					if not self.return_feedback:
						self.return_feedback = True
					self.stats_good(True, "silenced")
				else:
					self.return_feedback = False
					self.stats_good(True, "silence off")
				return

	
			# Compound support: run each sub-command in order
			sub_cmds =  self.split_compound(cmd)
			if type(sub_cmds) == type([]):
				if len(sub_cmds) > 1:
					if self.decideMyLog("all"): self.indiLOG.log(20, f"Compound command -> {sub_cmds}")
	
					for sub in sub_cmds:
						self.foundCommand = False # reset of multiple commands
						if not self.handle_wait(sub):
							if not self.execute_actions_for_command(sub):
								self.stats_good(False, "no match found")
							else:
								indigo.variable.updateValue(self.var_name_feedback, value=self.feedback_value)
			else:
				if not self.handle_wait(cmd):
					if not self.execute_actions_for_command(cmd):
						self.stats_good(False, "no match found")

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return 


	def execute_actions_for_command(self, cmd_in: str):
	
		# 1.1 check if this is something with explicit  xxxid:
		if  cmd_in.find("deviceid:") > -1 or cmd_in.find("variableid:") > -1:
			if self.try_pattern_commands(cmd_in): return
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"No match for '{cmd_in}' in ACTIONs or patterns")
			return False

		else:		
			# actionid:1234:
			# actionid:1234
			if  cmd_in.find("actionid:") > -1:
				self.foundCommand = True
				xx = cmd_in.strip(":").strip(" ").split("actionid:")
				if self.decideMyLog("Logic"): self.indiLOG.log(20, f'execute_actions_for_command action id :{xx}')
				if len(xx) == 2:
					id = int(xx[1].strip())
					if id in indigo.actionGroups:
						indigo.actionGroup.execute(id)
						self.stats_good(True, "action executed")
						if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands action executed ")
						return True
					if self.decideMyLog("Logic"): self.indiLOG.log(20, f' :{xx},  not present in indigo action groups')
					self.stats_good(False,"acton not present")
				self.stats_good(False,"acton not present")
				return True
		
			# 1.2 check if this is an action known under synonym:
			synonymId = int(self.synonymes_for_actions.get(cmd_in, 0))
	
			if synonymId != 0:
				self.foundCommand = True
				if self.decideMyLog("logic"): self.indiLOG.log(20, f"execute_actions_for_command '{cmd_in}' - action Id:{synonymId} = {indigo.actionGroups[synonymId].name}")
				indigo.actionGroup.execute(synonymId)
				self.stats_good(True, self.feedback_ok["action executed"])
				return True
	
				
		# second check if this is an dev var .. command:
		if self.try_pattern_commands(cmd_in): return True
		if self.foundCommand: return True

		if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"No match for '{cmd_in}' in ACTIONs or patterns")
		return False


	def try_pattern_commands(self, cmd_in: str) -> bool:
		try:
			# replace white spaces with one blank and strip blanks
			cmd = re.sub(r"\s+", " ", cmd_in.strip()).strip()
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands {cmd} ")

			self.device = []
			self.variable = []
			if cmd_in.find("deviceid:") > -1:
				if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands received devid ")
				aa = cmd_in.split("deviceid:")  
				# == turn on, devid: 
				# == turn on, devid
				# == bright, devid: (to) value
				# == bright, devid (to) value
				# == get, devid state statename
				# == get, devid: state statename
				
				if len(aa) == 2:
					if ":" in aa[1]:
						devid, value = aa[1].split(":")
						self.device = [aa[0], indigo.devices[int(devid)], value]
						if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands device: {self.device} ")
					else:
						pos = aa[1].find(" ")
						if pos > -1:
							devid = aa[1][:pos]
							value = aa[1][pos+1:]
							self.device = [aa[0], indigo.devices[int(devid)], value]
							if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands device: {self.device} ")
						else:
							devid = aa[1]
							value = ""
							self.device = [aa[0], indigo.devices[int(devid)], ""]
							if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands device: {self.device} ")
				else:
					self.stats_good(False,"id missing")
					self.foundCommand = True
					return False
	
			elif cmd_in.find("variableid:") > -1:
				# set variableid:13345: newvalue
				# set variableid:13345 newvalue
				# get variableid:13345:
				# get variableid:13345
				if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands received varid ")
				xx = cmd_in.split("variableid:")
				if len(xx) == 2:
					if ":" in xx[1]:
						valid, value = xx[1].split(":")
						self.variable = [xx[0], indigo.variables[int(valid)], value]
						if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands variable: {self.variable} ")
					else:
						pos = xx[1].find(" ")
						if pos > -1:
							valid = xx[1][:pos]
							value = xx[1][pos+1:]
							self.variable = [xx[0], indigo.variales[int(valid)], value]
							if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands variable: {self.variable} ")
						else:
							valid = xx[1]
							value = ""
							self.variable = [xx[0], indigo.variales[int(valid)], value]
							if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands variable: {self.variable} ")
				else:
					self.stats_good(False,"id missing")
					self.foundCommand = True
					return False

			###get variable or device / state value  ##
			if self.handle_get_value(cmd): return  True
			if self.foundCommand: return True

			### variables  first must have "set variable name to xx "
			if self.handle_set_variable(cmd): return  True
			if self.foundCommand: return True

			### devices ##
			if self.handle_set_speed(cmd): return True
			if self.foundCommand: return True

			if self.handle_beep(cmd): return True
			if self.foundCommand: return True

			if self.handle_pulse(cmd): return True
			if self.foundCommand: return True

			if self.handle_lock(cmd): return True
			if self.foundCommand: return True
			
			if self.handle_unlock(cmd): return True
			if self.foundCommand: return True
			
			if self.handle_turn_on_off(cmd): return True
			if self.foundCommand: return True
	
			if self.handle_toggle(cmd): return  True
			if self.foundCommand: return True

			if self.handle_set_heat(cmd): return  True
			if self.foundCommand: return True

			if self.handle_set_cool(cmd): return  True
			if self.foundCommand: return True

			if self.handle_set_level(cmd): return  True
			if self.foundCommand: return True

			return False
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)


	# ==========================
	#  META COMMANDS
	# ==========================
	
	def log_available_commands(self):
		self.indiLOG.log(20,"Available ACTION commands: that are mapped from voice to actual indigo action groups")
		for cmd in sorted( self.synonymes_for_actions.keys()):
			self.indiLOG.log(20, f"  {cmd}")
	
	def log_devices(self):
		self.indiLOG.log(20,"Device list (name → normalized) [truncated if large]:")
		count = 0
		for dev in indigo.devices:
			if count >=  self.list_devices_max:
				self.indiLOG.log(20, f"... truncated at {self.list_devices_max} devices ...")
				break
			self.indiLOG.log(20, f"   {dev.name:55} → {self.normalize_for_match(dev.name)}")
			count += 1

	# ==========================
	#  device/ var EXECUTION
	# ==========================


	# handle updates
	def handle_wait(self, cmd_in: str) -> bool:
		if cmd_in.find(self.translate["wait"]) > -1:
			self.foundCommand = True
			self.indiLOG.log(20, f"handle_wait received command: '{cmd_in}'")
			level = cmd_in.lower().split(self.translate["wait"])[1]
			level = self.map_to_float(level.strip()) # one --> 1
			self.sleep(level)
			self.stats_good(True, self.feedback_ok["wait"])
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_wait '{cmd_in}'wait for  {level} secs")
			return True
		return False


	def handle_set_speed(self, cmd_in: str) -> bool:
		
		#  cmd:  (set) speed device (to) xx
		pos = cmd_in.find(self.translate["speed"]+" ")
		if pos < 0: return False
		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_speed '{cmd_in}' speed at pos {pos}")

		if self.device != []:
			level = self.device[2].split(" ")[-1]
			dev = self.device[1]
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_speed '{dev.name}' speed {level}")

		else:			
			cmd = cmd_in.split(self.translate["speed"]+" ")[1]
	
			cmd1 = cmd.split(" "+self.translate["to"]+" ")
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_speed speed '{cmd}'")
			if len(cmd1) == 2:
				theName = cmd1[0]
				level = cmd1[1].strip()
			else:  # now without " "+self.translate["to"]+" " assume last word is level
				pos = cmd.rfind(" ")
				level = cmd[pos+1:].strip()
				theName = cmd[:pos].strip()
				if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_speed rfind '{pos}'")
		
			if pos < 5: return False
			theName, level = cmd.split(" "+self.translate["to"]+" ")
			dev = self.check_if_match_devices(theName)
			if not dev:
				if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"handle_set_speed No device found matching '{theName}'")
				return False
			if "speedLevel" not in dev.states: 
				if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"handle_set_speed No device '{theName}' does not have speed control")
				self.stats_good(False, self.feedback_bad["speed"]+" device not found")
				return False

			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_speed found '{theName}' {level}")
				
		try:
			level = self.map_to_int(level.strip()) # one --> 1
			indigo.speedcontrol.setSpeedIndex(dev.id, value=level)
			self.stats_good(True, self.feedback_ok["speed"])
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_speed '{dev.name}' speed {level}")
			return True
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"setspeed of {} failed".format(dev.name), exc_info=True)
		self.stats_good(False, self.feedback_bad["speed"])
		return True


	def handle_set_level(self, cmd_in: str) -> bool:
		
		# allow:
		#  set brightness level device to 66 %
		#  set brightness level device to 66 percent
		#      brightness level device to 66 %
		#      bright device to 66 %
		#      bright device 66 %
		#      bright device 66 
		#   ...

		pos = cmd_in.find(self.translate["bright"])
		if pos < 0: return False
		self.foundCommand = True

		if self.device != []:
			cmd = self.device[2].strip(" ")
			cmd = cmd.strip("%")
			cmd = cmd.strip("percent")
			cmd = cmd.strip(" ")
			level = cmd.split(" ")
			if len(level) == 1:   level = level[0]
			elif len(level) == 2: level = level[1] 
			else:                 level = level[-1] 
			dev = self.device[1]
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_level '{dev.name}' to {level}")

		else:	
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_level '{cmd_in}' bright at pos {pos}")
			# remove %  spaces 
			cmd = cmd_in.strip(" ")
			cmd = cmd.strip("%")
			cmd = cmd.strip("percent")
			cmd = cmd.strip(" ")
			pos = cmd.find(" ")
			# now remove  first word bright(ness)
			cmd = cmd[pos+1:].strip()
			# check if level preset 
			pos = cmd.find(self.translate["level"]+" ")
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_level '{cmd}' level at pos {pos}")
			if pos == 0: #remove " level "
				cmd = cmd[len(self.translate["level"]+" "):].strip()
			
			# we should now have "device to xx"
			#     or             "device xx"  also ok
			cmd1 = cmd.split(" "+self.translate["to"]+" ")
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_level to '{cmd}'")
			if len(cmd1) == 2:
				theName = cmd1[0]
				level = cmd1[1].strip()
			else:  # now without " "+self.translate["to"]+" " assume last word is level
				pos = cmd.rfind(" ")
				level = cmd[pos+1:].strip()
				theName = cmd[:pos].strip()
				if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_level rfind '{pos}'")
	
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_level1  dev {theName}, level:{level}%")
			dev = self.check_if_match_devices(theName)
			if not dev:
				if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"handle_set_level No device found matching '{theName}'")
				self.stats_good(False, self.feedback_bad["bright"]+" device not found")
				return True

		level = self.map_to_int(level.strip()) # one --> 1

		level = max(0, min(100, int(level)))

		if self.device_is_dimmable(dev):
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"Setting dev '{dev.name}' to {level}%")
			try:
				indigo.dimmer.setBrightness(dev.id, value=level)
				self.stats_good(True, self.feedback_ok["bright"])
			except	Exception as e:
				if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
				self.stats_good(False, self.feedback_bad["bright"])
			return True

		# relay fallback: >0 => ON, 0 => OFF
		if level == 0:
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"Setting dev '{dev.name}' to 0% (relay -> OFF)")
			try:
				indigo.device.turnOff(dev.id)
				self.stats_good(True, self.feedback_ok["bright"])
			except Exception as e:
				self.stats_good(False, self.feedback_bad["bright"])
				self.indiLOG.log(20, f"Error turning off '{dev.name}': {e}")
		else:
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"Setting dev '{dev.name}' to {level}% (relay -> ON)")
			try:
				indigo.device.turnOn(dev.id)
				self.stats_good(True, self.feedback_ok["bright"])
				return True
			except	Exception as e:
				if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"set brightness of {} failed".format(dev.name), exc_info=True)

		self.stats_good(False, self.feedback_bad["bright"])
		return True


	def handle_unlock(self, cmd_in: str) -> bool:
	
		pos = cmd_in.find(self.translate["unlock"]+" ")
		if pos < 0: return False
		self.foundCommand = True

		if self.device != []:
			dev = self.device[1]
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_unlock '{dev.name}'")
			indigo.device.unlock(dev.id)
			self.stats_good(True, self.feedback_ok["unlock"])
			return True
				

		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_unlock '{cmd_in}'  unlock at pos {pos}")
		theName = cmd_in.split(self.translate["unlock"]+" ")[1]

		dev = self.check_if_match_devices(theName)
		if not dev:
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"handle_unlock No device found matching '{theName}'")
			self.stats_good(False, self.feedback_bad["unlock"]+" device not found")
			return True

		try:
			indigo.device.unlock(dev.id)
			self.stats_good(True, self.feedback_ok["unlock"])
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"unlock dev '{dev.name}'")
			return True
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"unlock of {} failed".format(dev.name), exc_info=True)
		self.stats_good(False, self.feedback_bad["unlock"])+" command not available"
		return True


	def handle_lock(self, cmd_in: str) -> bool:
	
		pos = cmd_in.find(self.translate["lock"]+" ")
		if pos < 0: return False
		self.foundCommand = True

		if self.device != []:
			dev = self.device[1]
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_lock '{dev.name}'")
			indigo.device.lock(dev.id)
			self.stats_good(True, self.feedback_ok["lock"])
			return True

		if self.decideMyLog("Logic"): self.indiLOG.log(20, f'handle_lock "{cmd_in}""  "lock"  found @ {pos}')
		theName = cmd_in.split(self.translate["lock"]+" ")[1]

		dev = self.check_if_match_devices(theName)
		if not dev:
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"handle_lock No device found matching '{theName}'")
			self.stats_good(False, self.feedback_bad["lock"]+" device not found")
			return True

		try:
			indigo.device.lock(dev.id)
			self.stats_good(True, self.feedback_ok["lock"])
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_lock lock dev '{dev.name}'")
			return True
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"lock of {} failed".format(dev.name), exc_info=True)
		self.stats_good(False, self.feedback_bad["lock"]+" command not available")
		return True



	def handle_beep(self, cmd_in: str) -> bool:
	
		pos = cmd_in.find(self.translate["beep"]+" ")
		if pos < 0: return False
		self.foundCommand = True


		if self.device != []:
			dev = self.device[1]
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_beep '{dev.name}'")
			indigo.device.beep(dev.id)
			self.stats_good(True, self.feedback_ok["beep"])
			return 


		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_beep '{cmd_in}'  beep at pos {pos}")
		theName = cmd_in.split(self.translate["beep"]+" ")[1]

		dev = self.check_if_match_devices(theName)
		if not dev:
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"Nhandle_beep o device found matching '{theName}'")
			self.stats_good(False, self.feedback_bad["beep"]+" device not found")
			return True

		if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_beep beep dev '{dev.name}'")
		try:
			indigo.device.beep(dev.id)
			self.stats_good(True, self.feedback_ok["beep"])
			return True
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"beep of dev:{} failed".format(dev.name), exc_info=True)
		self.stats_good(False, self.feedback_bad["beep"])
		return True


	def handle_pulse(self, cmd_in: str) -> bool:
		# pulse <device> 5 (seconds)
		pos = cmd_in.find(self.translate["pulse"])
		if pos != 0: return False
		self.foundCommand = True

		if self.device != []:
			dev = self.device[1]
			level = self.device[2]
			if level.find("sec"):
				level = level.split(" ")[0]
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_pulse '{dev.name}', pulse:{level} secs")

		else:
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_pulse '{cmd_in}'  pulse at pos {pos}")
			rest = cmd_in.split(" ")
			if rest[-1].find("sec"):
				level = cmd[-2]
				theName = " ".join(rest[:-2])
			else:	
				level = cmd[-1]
				theName = " ".join(cmd[1:-1])
			
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_pulse dev {theName}, secs {level}")
	
			dev = self.check_if_match_devices(theName)
			if not dev:
				if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"handle_pulse No device found matching '{theName}'")
				self.stats_good(False, self.feedback_bad["pulse"]+" device not found")
				return True
	
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_pulse turn on  dev '{dev.name}' for secs  {level}")

		try:
			level = self.map_to_float(level.strip()) # one --> 1
		except: level = 1.

		try:	
			indigo.device.turnOn(dev.id)
			self.stats_good(True, self.feedback_ok["pulse"])
			self.sleep(level)
			indigo.device.turnOff(dev.id)
			return True
			
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"handle_pulse of {} failed".format(dev.name), exc_info=True)
			self.stats_good(False, self.feedback_bad["pulse"])
		return True
	
	def handle_turn_on_off(self, cmd_in: str) -> bool:
		# turn on / off<device>
		pos = cmd_in.find(self.translate["turn"])
		if pos != 0: return False
		self.foundCommand = True

		if self.device != []:
			dev = self.device[1]
			turn = self.device[0].strip()
			state = turn.split(" ")[1]
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_turn_on_off w devId:: '{dev.name}', turn:{turn}, state:{state}")

		else:
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_turn_on_off w devname cmd: '{cmd_in}'  turn at pos {pos}")
			cmd = cmd_in[pos+4:].strip() # removed "turn "
			cmd = cmd.split(" ") # first is on / off 
			state = cmd[0].strip()
			theName = (" ").join(cmd[1:]).strip() # rest is dev name 
			
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_turn_on_off devname: {theName}, turn {state}")
	
			dev = self.check_if_match_devices(theName)
			if not dev:
				if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"No device found matching '{theName}'")
				self.stats_good(False, self.feedback_bad["turn"]+" device not found")
				return True
	
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"Turning dev name'{dev.name}' to  {state}")

		try:
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f'Turning on: {self.translate["on"]}  with turn=  {state}')
			if state == self.translate["on"]:
				if self.device_is_dimmable(dev):
					if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"Turning dev '{dev.name}' to  {state} using setbrightness 100")
					indigo.dimmer.setBrightness(dev.id, value=100)
				else:
					if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"Turning dev '{dev.name}' to  {state} using turnOn")
					indigo.device.turnOn(dev.id)
			else:
				if self.device_is_dimmable(dev):
					if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"Turning dev '{dev.name}' to  {state} using setBrightness 0")
					indigo.dimmer.setBrightness(dev.id, value=0)
				else:
					if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"Turning dev '{dev.name}' to  {state} using turnOff")
					indigo.device.turnOff(dev.id)
			self.stats_good(True, self.feedback_ok["turn"])
			return True
			
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"turn_on_off of {} failed".format(dev.name), exc_info=True)
		self.stats_good(False, self.feedback_bad["turn"])
		return True


	def handle_toggle(self, cmd_in: str) -> bool:
	
		m = re.match(r"^"+self.translate["toggle"]+"\s+(?:the\s+)?(.+)$", cmd_in)
		if not m: return False
		self.foundCommand = True
	
		if self.device != []:
			dev = self.device[1]
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_toggle '{dev.name}'")
			indigo.device.toggle(dev.id)
			self.stats_good(True, self.feedback_ok["toggle"])
			return True
	
		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_toggle  m:{m.groups()}")
		theName = m.group(1)
		dev = self.check_if_match_devices(theName)
		if not dev:
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"handle_toggle No device found matching '{theName}'")
			self.stats_good(False, self.feedback_bad["toggle"]+" device not found")
			return True

		if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_toggle dev '{dev.name}'")

		try:
			indigo.device.toggle(dev.id)
			self.stats_good(True, self.feedback_ok["toggle"])
			return True
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"handle_toggle of {} failed".format(dev.name), exc_info=True)
		self.stats_good(False, self.feedback_bad["toggle"])
		return True


	def handle_set_heat(self, cmd_in: str) -> bool:
		# (set) heat <device> (to) xx 
		pos = cmd_in.find(self.translate["heat"]+" ")
		if pos < 0: return False
		self.foundCommand = True


		if self.device != []:
			level = self.device[2].split(" ")[-1]
			dev = self.device[1]
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_heat '{dev.name}' level {level}")

		else:
			rest = cmd_in.split(self.translate["heat"]+" ")[1]
			level = rest.split(" ")[-1]
			m = rest.split(" "+self.translate["to"]+" ")
			if len(m) == 2: 
				theName = m[0]
			else:
				theName = " ".join(rest.split(" ")[0:-1])
	
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_heat  m:{m}")
			dev = self.check_if_match_devices(theName)
			if not dev:
				if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"handle_set_heat No device found matching '{theName}'")
				self.stats_good(False, self.feedback_bad["heat"]+" device not found")
				return True
	
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_set_heat dev '{dev.name}' to {level} º")

		try:
			level = self.map_to_int(level.strip()) # one --> 1
			indigo.thermostat.setHeatSetpoint(dev.id, value=int(level))
			self.stats_good(True, self.feedback_ok["heat"])
			return True
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"setHeatSetpoint of {} failed".format(dev.name), exc_info=True)
		self.stats_good(False, self.feedback_bad["heat"])
		return True


	def handle_set_cool(self, cmd_in: str) -> bool:
		# (set) cool <device> (to) xx 
		pos = cmd_in.find(self.translate["cool"]+" ")
		if pos < 0: return False
		self.foundCommand = True
		
		if self.device != []:
			level = self.device[2].split(" ")[-1]
			dev = self.device[1]
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_cool '{dev.name}' level {level}")

		else:
			rest = cmd_in.split(self.translate["cool"]+" ")[1]
			level = rest.split(" ")[-1]
			m = rest.split(" "+self.translate["to"]+" ")
			if len(m) == 2: 
				theName = m[0]
			else:
				theName = " ".join(rest.split(" ")[0:-1])
				
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_cool m:{m}")
			dev = self.check_if_match_devices(theName)
			if not dev:
				if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"handle_set_cool No device found matching '{theName}'")
				self.stats_good(False, self.feedback_bad["cool"]+" device not found")
				return True
	
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_set_cool dev '{dev.name}' to {level} º")

		try:
			level = self.map_to_int(level.strip()) # one --> 1
			indigo.thermostat.setCoolSetpoint(dev.id, value=int(level))
			self.stats_good(True, self.feedback_ok["cool"])
			return True
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"setCoolSetpoint of {} failed".format(dev.name), exc_info=True)
		self.stats_good(False, self.feedback_bad["cool"]+" device not found")
		return True


	def handle_set_variable(self, cmd_in: str) -> bool:
		# set variable <varname> to value
		pos = cmd_in.find(self.translate["set"]+" "+self.translate["variable"]+" ")
		if pos < 0: return False
		self.foundCommand = True

		if self.variable != []:
			level = self.variable[2].split(" ")[-1]
			var = self.variable[1]
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_variable '{var.name}' level {level}")

		else:
		    
			rest = cmd_in.split(self.translate["set"]+" "+self.translate["variable"]+" ")[1]
			if " "+self.translate["to"]+" " not in rest: return  False
			
			theName, value = rest.split(" "+self.translate["to"]+" ")
			
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_variable   variable:{theName}  to {level}")
			var = self.check_if_match_variables(theName)
			if not var:
				if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"handle_set_variable No Variable found matching '{theName}'")
				self.stats_good(False, self.feedback_bad["set"]+" variable not found")
				return True
	
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_set_variable update var '{var.name}' to {level}")
	
		level = self.map_to_int(value.strip()) # one --> 1
		try:
			indigo.variable.updateValue(var.name, value=str(level))
			self.stats_good(True, self.feedback_ok["set"])
			return True
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"updateValue of {} failed".format(var.name), exc_info=True)
		self.stats_good(False, self.feedback_bad["set"])
		return True


	def handle_get_value(self, cmd_in: str) -> bool:
		#  command :=  get device xx state yy 
		#  command :=  get variable varname  
		pos = cmd_in.find(self.translate["get"]+" ")
		if pos != 0: return False
		if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_get_value var '{cmd_in}' pos {pos}")
		self.foundCommand = True

		if self.device == []:
			var = False
			if self.variable != []:
				var = self.variable[1]
				if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_get_value '{var.name}' value {var.value}")
	
			else:
				cmd = cmd_in.split(self.translate["get"]+" ")[1]
				pos = cmd.find(self.translate["variable"]+" ")
				if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_get_value var '{cmd}' pos {pos}")
				if pos == 0: 
					cmd = cmd.split(self.translate["variable"]+" ")[1]
					var = self.check_if_match_variables(cmd)
			if var:
				self.stats_good(True, var.value)
				if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_get_value var '{var.name}' value:{var.value}")
			
		# check devices
		if self.device != []:
			dev = self.device[1]
			state = self.device[2].strip()
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_get_value  in DEVICE  try '{dev.name}, {state}")
		else:
			cmd = cmd_in[4:].strip()
			xx = cmd.split(" state ")
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f'handle_get_value dev  split" State " {xx}')
			if len(xx) < 2: 
				self.stats_good(True, "state not defned")
				return True
			devName, state = xx
			dev = self.check_if_match_devices(devName)
			if not dev: 
				self.stats_good(False, self.feedback_bad["get"]+" variable not found")
				return True
			state = state.strip()
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_get_value dev '{devName}' {state} ")
		for yy in dev.states:
			#if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_get_value testing {xx} >{xx.lower()}< == >{state}< , { xx.lower() == state}")
			if self.normalize_for_match(yy) == state:
				value = str(dev.states[yy])
				self.stats_good(True, value)
				if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_get_value  {dev.name}  state:{value} found ")
				return True
		if self.decideMyLog("Logic"): self.indiLOG.log(20, f'handle_get_value  no state: "{state}" found ')
					
		self.stats_good(False, self.feedback_bad["get"])
		return True


	# ==========================
	#  utils for parsing, comparison.. 
	# ==========================

	def apply_PhraseMappings(self, p: str) -> str:
		if not p:
			return p
		s = p.lower()
		for bad in self.map_from_to:
			if bad in s:
				s = s.replace(bad, self.map_from_to[bad])
			#s = re.sub(r"\""+toBeReplaced+"\b", self.REPLACE_STRINGS_WITH[toBeReplaced], s) # replace lamp with light .. etc
		return s


	def is_blocked_device_name(self, p: str) -> bool:
		if not p:
			return False
		s = p.lower()	
		for test in  self.blocked_words:
			if test in s: return True
			
		return False


	def check_if_time_tag_ok(self, test_in: str) -> (bool, str):
		messageTime = test_in.split()[0].lower()
		if not  self.expect_time_tag:
			# remove time since epoch tag if present 
			try: 
				float(messageTime)
				return True, test_in[len(messageTime)+1:].strip()
			except:
				return True, test_in
				
		try:
				messageTimeNumber = float(messageTime)
		except:
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"Ignoring '{test_in}'; bad time info, not a number")
			return
		
		dt = time.time() - messageTimeNumber
		if dt >  self.allow_delta_time:
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"Ignoring '{test_in}'; time not in allowed window: {dt:.1f}")
			return False, test_in
			
		if self.decideMyLog("Logic"):self.indiLOG.log(20, f"accepted  '{test_in}'; time in allowed window: {dt:.1f}")
		
		return True, test_in[len(messageTime):].strip()


	## for indigo dev  var names and state names 
	def normalize_for_match(self, p: str) -> str:
		if p is None:
			return ""
		# replace outsideLamp with outside lamp
		# replace outside_Lamp with outside lamp
		# replace outside-Lamp with outside lamp
		# replace outside- Lamp with outside lamp
		s = re.sub(r'(?<!^)(?=[A-Z])', ' ', p).lower() # abcDef -> abc def
		s = re.sub(r"[\/_\-]", " ", s) # replace / _ - with one blank 
		s = re.sub(r"\s+", " ", s) # replace multiple white spaces with one blank 
		return s.strip()


	# for all incoming command 
	def normalize_command(self, p: str) -> str:
		if p is None:
			return ""
		# replace outsideLamp with outside lamp
		# replace outside_Lamp with outside lamp
		# replace outside-Lamp with outside lamp
		# replace outside- Lamp with outside lamp
		# replace bad strings with good  eg the bug --> debug if set 
		s = re.sub(r'(?<!^)(?=[A-Z])', ' ', p).lower() # # abcDef -> abc def
		s = re.sub(r"\s+", " ", s).strip()# replace multiple white spaces with one blank and no blank at the end
		s =  self.apply_PhraseMappings(s)
		s = re.sub(r"\s+", " ", s)# replace multiple white spaces with one blank and no blank at the end
		return s.strip()


		# map speed to a number 
	def map_to_int(self, level:str):
		if level in _mapNumbertextToInt:
			level = _mapNumbertextToInt[level]
		else:
			try: level = int(level)
			except: pass
		return level


	def map_to_float(self, level:str):
		try: 
			xx = float(level)
			return xx
		except: pass
		try:
			xx = float(map_to_int(level))
			return float(xx)
		except: pass
		return level			


	def device_is_dimmable(self, dev) -> bool:
		try:
			return ("brightnessLevel" in dev.states) or ("dimLevel" in dev.states)
		except Exception:
			return False


	def check_if_match_devices(self, theName: str):
		
		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"check_if_match_device  {theName}")

		if self.is_blocked_device_name(theName): return None
		
		if theName in indigo.devices:
			return indigo.devices[theName]
			
		for dev in indigo.devices:
			indigoName = self.normalize_for_match(dev.name)
			if indigoName.find(theName) > -1:
				return dev

		id = self.synonymes_for_devices.get(theName, 0)
		try: 
			id = int(id)
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"check_if_match_devices  {theName} / {id},  in indigo?:{id in indigo.devices}")
		except: return None
		 
		try:
			xxx = indigo.devices[id]
			return xxx
		except: pass
		return  None


	def check_if_match_variables(self, theName):
		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"check_if_match_variables  {theName}")
	
		if self.is_blocked_device_name(theName): return None

		if theName in indigo.variables:
			return indigo.variables[theName]

		for var in indigo.variables:
			indigoName = self.normalize_for_match(var.name)
			if indigoName.find(theName) >-1:
				return var
		
		id = self.synonymes_for_variables.get(theName, 0)
		try: 
			id = int(id)
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"check_if_match_variables {theName} / {id},  in indigo?:{id in indigo.variables}")
		except: return None
		 
		try:
			xxx = indigo.variables[id]
			return xxx
		except: pass
		return  None


	def set_feedback_value_ok(self, value_in:str):
		if not self.return_feedback:
			if value_in != "":	self.feedback_value = value_in
			else:				self.feedback_value = self.return_ok
		if self.return_feedback == "detailed":
			if value_in != "":	self.feedback_value = value_in
			else:				self.feedback_value = "ok"
		elif self.return_feedback == "simple":
								self.feedback_value = "ok"
		else:
								self.feedback_value = " "


	def set_feedback_value_bad(self, value_in:str):
		if self.return_feedback == "detailed":
			if value_in != "":	self.feedback_value = value_in
			else:				self.feedback_value = "not executed"
		elif self.return_feedback == "simple":
								self.feedback_value = "not executed"
		else:
								self.feedback_value = " "
								
	def split_compound(self, cmd: str):
		"""
		Split on 'and' / 'then' / '&' with spaces.
		Example: 'unmute tv and set tv to 24' -> ['unmute tv', 'set tv to 24']
		"""
		if not cmd:					return cmd
		if " and " in cmd:			return cmd.split(" and ")
		if " then " in cmd:			return cmd.split(" then ")
		if "&" in cmd:				return cmd.split("&")
		if True:					return cmd


	def stats_good(self, good: bool, retText):
		"""
		write ot success fail to json and send back message to iphne
		"""
		pos = self.raw.find(" ")
		cmdOnly = self.raw[pos+1:].strip() # no time stamp 
		self.finished = True
				
		if not good:
			if cmdOnly not in self.failed_commands:
				self.failed_commands[cmdOnly] = []
			self.set_feedback_value_bad(retText)
			self.failed_commands[cmdOnly].append( datetime.datetime.now().strftime(_defaultDateStampFormat))
			self.writeJson(self.failed_commands, fName=self.indigoPreferencesPluginDir + "failed_commands.json")
		else:
			self.set_feedback_value_ok(retText)
			if cmdOnly not in self.ok_commands:
				self.ok_commands[cmdOnly] = []
			self.ok_commands[cmdOnly].append( datetime.datetime.now().strftime(_defaultDateStampFormat))
			self.writeJson(self.ok_commands, fName=self.indigoPreferencesPluginDir + "ok_commands.json")
		return 	


	####-----------------	 ---------
	def decideMyLog(self, msgLevel: int):
		try:
			if msgLevel	 == "All" or "All" in self.debugAreas:		return True
			if msgLevel	 == ""  and "All" not in self.debugAreas:	return False
			if msgLevel in self.debugAreas:							return True

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return False


###-----------------  valiable formatter for differnt log levels ---------
# call with: 
# formatter = LevelFormatter(fmt='<default log format>', level_fmts={logging.INFO: '<format string for info>'})
# handler.setFormatter(formatter)
class LevelFormatter(logging.Formatter):
	def __init__(self, fmt=None, datefmt=None, level_fmts={}, level_date={}):
		self._level_formatters = {}
		self._level_date_format = {}
		for level, format in level_fmts.items():
			# Could optionally support level names too
			self._level_formatters[level] = logging.Formatter(fmt=format, datefmt=level_date[level])
		# self._fmt will be the default format
		super(LevelFormatter, self).__init__(fmt=fmt, datefmt=datefmt)
		return


	####-----------------	 ---------
	def format(self, record):
		if record.levelno in self._level_formatters:
			return self._level_formatters[record.levelno].format(record)

		return super(LevelFormatter, self).format(record)

