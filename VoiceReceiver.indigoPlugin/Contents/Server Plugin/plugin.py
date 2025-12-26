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

_mapNumbertextToInt = {"null":0, "one":1, "two":2, "three":3, "four":4, "five":5, "six":6, "seven":7, "eight":8, "nine":9}

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
	"blocked_device_words":					"alarm|lock",
	"return_ok":							"ok",
	"return_bad":							"not sucessful",
	"return_silent":						False,
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
		
####

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

			self.actions = {}
			test = self.readJson(self.indigoPreferencesPluginDir+"actions.json", defReturn={})
			if test != {}:
				self.actions = test

			self.synonymes_for_actions    = self.readJson(self.indigoPreferencesPluginDir+"synonymes_for_actions.json", defReturn={})
			self.synonymes_for_devices    = self.readJson(self.indigoPreferencesPluginDir+"synonymes_for_devices.json", defReturn={})
			self.synonymes_for_variables  = self.readJson(self.indigoPreferencesPluginDir+"synonymes_for_variables.json", defReturn={})

			self.map_from_to = {
					"hieu": "hue",
					"hugh": "hue",
			}

			test  = self.readJson(self.indigoPreferencesPluginDir+"map_from_to.json", defReturn={})
			if test != {}:
				self.map_from_to  = test

			self.blocked_device_words = self.pluginPrefs.get("blocked_device_words", kDefaultPluginPrefs["blocked_device_words"]).split("|")

			test = self.readJson(self.indigoPreferencesPluginDir+"blocked_device_words.json", defReturn={})
			if test != {}:
				self.blocked_device_words = test
			
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

			self.return_ok = self.pluginPrefs.get("return_ok", kDefaultPluginPrefs["return_ok"])	
			self.return_bad = self.pluginPrefs.get("return_bad", kDefaultPluginPrefs["return_bad"])	
			self.return_silent = self.pluginPrefs.get("return_silent", kDefaultPluginPrefs["return_silent"])	
			
	
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
			yy = ("|").join(self.blocked_device_words)
			xx[0]["blocked_device_words"] = yy
		return xx
		
	####-----------------  ---------
	#### good bad words 
	####-----------------  ---------
	def blockWordsCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20, f"blockWordsCallback {valuesDict}")
		self.blocked_device_words = valuesDict["blocked_device_words"].split("|")
		self.writeJson({"blocked_device_words":self.blocked_device_words}, fName=self.indigoPreferencesPluginDir + "blocked_device_words.json", sort = True, doFormat=True, singleLines= False )


	####-----------------  ---------
	def addFromCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20, f"selectActionsCallback {valuesDict}")
		bad = valuesDict["from"]
		good = valuesDict["to"]
		if bad not in self.map_from_to:
			self.map_from_to[bad] = good
		self.writeJson(self.map_from_to, fName=self.indigoPreferencesPluginDir + "map_from_to.json", sort = True, doFormat=True, singleLines= False )

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
	#### define actions to be enabled  / removed
	####-----------------  ---------
	def actionNumberConfirmCallback(self, valuesDict=None, typeId=""):
		self.actionNumber = int(valuesDict["actionNumber"])
		self.actionId = 0
		xList = []
	
		for bad in self.map_from_to:
			xList.append([bad, bad])
		#self.indiLOG.log(20, f"filterWords xList: {xList}")
		return xList

	def addActionsCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20, f"selectActionsCallback {valuesDict}")
		if self.actionNumber == 0: return 
		actionId = int(valuesDict["add"])

		definedAction = indigo.actionGroups[actionId].name
		self.actions[definedAction] = [actionId, self.actionNumber]
		#self.indiLOG.log(20, f"selectActionsCallback actionId:  {actionId}, :{definedAction}, {self.actions}")
					
		self.writeJson(self.actions, fName=self.indigoPreferencesPluginDir + "actions.json", sort = True, doFormat=True, singleLines= False )


	def delActionsCallback(self, valuesDict=None , typeId=""):
		s#elf.indiLOG.log(20, f"delActionsCallback {valuesDict}")
		if self.actionNumber == 0: return 
		
		delAction = -1
		for definedAction in self.actions:
			if self.actions[definedAction][1] == self.actionNumber: #already defined, keep
				delAction = definedAction
				break
				
		#self.indiLOG.log(20, f"delActionsCallback  actionNumber: {self.actionNumber}, delAction:{delAction},")
		if delAction == -1: return 
		del self.actions[definedAction]
		self.writeJson(self.actions, fName=self.indigoPreferencesPluginDir + "actions.json", sort = True, doFormat=True, singleLines= False )


	####-----------------  ---------
	#### define synonymes for actions
	####-----------------  ---------
	def filterActions(self, filter="", valuesDict=None , typeId=None):
		# also used to enable and disable actions 
		xList = []
	

		if filter  == "synonymes":
			for action in self.actions:
				xList.append([self.actions[action][0], action])
			return xList

		if self.actionNumber == 0: return xList

		if filter == "remove":
			for action in self.actions:
				nn = self.actions[action][1]
				if nn == self.actionNumber:
					xList.append(["0",action])
					break
			#self.indiLOG.log(20, f"filterActions {xList}")
			return xList


		if filter == "add":
			for action in indigo.actionGroups.iter(self.pluginId):
				name = action.name
				actionN = action.id
				#self.indiLOG.log(20, f"action: {name}, {actionN}")
				if name not in self.actions:
					xList.append([action.id, name])
					continue
							
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
		s#elf.indiLOG.log(20, f"selectActionsCallback {valuesDict}")
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
	def printConfig(self,  valuesDict=None , typeId=""):
		try:
			out =  '\n'
			out += '#########################################################################\n'
			out += ' credit must go to @dtich on the indigo forum who came up with the script\n'
			out += '#########################################################################\n'
			out += '\n'
			out += 'What does it do?\n'
			out += '  the plugin \n'
			out += '  - receives message in indigo variable from iphone dictation shortcut \n'
			out += '  - analyses the received string to look for commands to \n'
			out += '    --   start indigo actions (must be defined inplugin menu)\n'
			out += '    --   switch on/off or dim devices , ... \n'
			out += '  - sends back  ok / not sucessful (you can set) and the iphone speaks that text\n'
			out += '  - you can define text mapping (bad to good) and black lists of devices / action that should be be executed\n'
			out += '  the shortcut on the iphone / mac/ ipad/..  \n'
			out += '  - listens to command \n'
			out += '  - sends command into indigo variable \n'
			out += '  - receives result from variable \n'
			out += '  - speaks result  (ok bad)\n'
			out += '\n'
			out += '\n'
			out += '================================ INSTALL ===========================\n'
			out += '(A) In plugin define the configurations in plugin config and menu\n'
			out += '\n'
			out += '(B) === Create shortcut on iPhone with the following items: ====\n'
			out += '  you can download a shortcut with empty keys etc at https://www.icloud.com/shortcuts/afc43a0555e04fbfa5b26f2953b3e274\n'
			out += '   then replace the bearer key, your indigo variable ids (2), the local ip of you indigo server, and the the first part of the iphone local wifi ip # to detect if you are at home   \n'
			out += '\n'
			out += '= manual creation:\n'
			out += '1. Dismiss Siri and Continue                                         to shorten pause \n'
			out += '2. Dictate text                                                      this is where the voice gets recorded\n'
			out += '3. Current Date                                                      create date object  \n'
			out += '3. Get Seconds between 1970-01-01 0:00 z and Date                    create time since epoch in secs  \n'
			out += '4. Text "Time Between Dates" "Dictated Text"                         create text string to be send timestamp space command\n'
			out += '5. get current IP Address (local)                                    \n'
			out += '6. if Current IP Address contains 192.                               use you local ip number start here\n'
			out += '6.1. Get contents of https://ip of indigo server:8176/v2/api/command  for local indigo contact  \n'
			out += '6.2.   method Post\n'
			out += '6.3.   Headers\n'
			out += '6.3.1    Authorization  Bearer <your id string> 					 from indigo web page \n'
			out += '6.3.1    Content-Type applicatio/json\n'
			out += '6.4    Request Body: JSON\n'
			out += '6.4.1    message : Text indigovariable.updateValue\n'
			out += '6.4.2    objectId : <indigo variable id>                             here you put the indigo variable id\n'
			out += '6.4.3    parameters : Dictionary\n'
			out += '6.4.3.1    value  Text: Text                                         this is the varibale that contains time space command\n'
			out += '7.1. Get contents of http://ip of indigo server:8176/v2/api/variable/12345     \n'
			out += '7.2.   method get\n'
			out += '7.3.   Headers\n'
			out += '7.3.1    Authorization  Bearer <your id string> 					 from indigo web page \n'
			out += '7.3.1    Content-Type applicatio/json\n'
			out += '7.4  get value for value in get contents of URL\n'
			out += '7.5  speak Dictionary value                                          this will speak the reslt send back from the plugin ok/ bad\n'
			out += '8. Otherwise \n'
			out += '8.1. Get contents of https://<yourid>indigodome.net/v2/api/command   indigo exernal contact  \n'
			out += '8.2.   method Post\n'
			out += '8.3.   Headers\n'
			out += '8.3.1    Authorization  Bearer <your id string> 					 from indigo web page \n'
			out += '8.3.1    Content-Type applicatio/json\n'
			out += '8.4    Request Body: JSON\n'
			out += '8.4.1    message : Text indigovariable.updateValue\n'
			out += '8.4.2    objectId : <indigo variable id>                             here you put the indigo variable id\n'
			out += '8.4.3    parameters : Dictionary\n'
			out += '8.4.3.1  value  Text: Text                                           this is the varibale that contains result text\n'
			out += '9.1. Get contents of https://<yourid>indigodome.net/v2/api/variable/12345     \n'
			out += '9.2.   method get\n'
			out += '9.3.   Headers\n'
			out += '9.3.1    Authorization  Bearer <your id string> 					 from indigo web page \n'
			out += '9.3.1    Content-Type applicatio/json\n'
			out += '9.4  get value for value in get contents of URL\n'
			out += '9.5  speak Dictionary value                                          this will speak the reslt send back from the plugin ok/ bad\n'
			out += '10. name it eg "indigo" \n'
			out += '11. share to desktop\n'
			out += '12. \n'
			out += '=== END create shortcut  ...  ====\n'
			out += '\n'
			out += '13. speaking "hey Siri Indigo" pause "turn on office lights"  \n'
			out += '    you could also define eg "hey indigo do" as hey siri replacement for this shortcut:   \n'
			out += '     settings / Accessibility  / voval short cuts / add action / select yor shorcut say "hey indigo do" 3 times  save  \n'
			out += '14. if you have a light named office lights:  \n'
			out += '     "hey indigo do"  pause  "turn on office lights"  should turn on your office lights    \n'
			out += '\n'
			out += '\n'
			out += '====  commands ====================================================\n'
			out += '   substitute <device> with device name or synonym   \n'
			out += '   substitute <variable> with variable name or synonym   \n'
			out += '   substitute <state> with state name  \n'
			out += '   set variable <variable> to value                                  write value to variable\n'
			out += '   get variable <variable>                                           get var value and speak it\n'
			out += '   get <device> state <state>                                        get dev/state value and speak it\n'
			out += '                                                                     notice the differnce to get variable \n'
			out += '   speed <device> to xx                                              for fans; (0-4 or 100)  one, two mapped to 1, 2\n'
			out += '   beep <device>  \n'
			out += '   lock <device>  \n'
			out += '   unlock <device>  \n'
			out += '   turn on/off <device>                                              \n'
			out += '   toggle <device>  \n'
			out += '   heat <device> to degrees                                          for thermostates\n'
			out += '   cool <device> to degrees                                          for thermostates\n'
			out += '   bright(en) <device> to xx (percent)                                   for dimmers, brightness (xx = 0..100)  \n'
			out += '   action_name  (name and action id must be set in menu)  \n'
			out += '\n'
			out += '   bright <device> to xx and <action> and  turn on <device2>         will execute 3 commands  \n'
			out += '   the execution is checked in the sequence to make sure that they are not ambigous\n'
			out += '\n'
			out += '=== meta commands ==================================================\n'
			out += '  list devices                                                       will print add devices to logfile  \n'
			out += '  list actions   or  what can you do                                 will print all defined  ndigo actions setup in this plugin \n'
			out += '  debug on                                                           will enable debug all \n'
			out += '  debug off                                                          will disable debug all \n'
			out += '  test                                                               will print "test" to logfile \n'
			out += '  help                                                               will print this to logfile \n'
			out += '\n'
			out += ' upper and lower cases are ignored\n'
			out += '\n'
			out += 'in menue you can define:\n'
			out += '1. action names and ids to be executed \n'
			out += '1. synonymes for devices, variables, actions \n'
			out += '2. mappings of bad to good words (eg lamp to lights)  the plugin will replace the bad strings with the good\n'
			out += '\n'
			out += '\n'
			out += '\n =============plugin config Parameters========\n'
			out += f'allow_delta_time       = {self.allow_delta_time}\n'
			out += '                          message must not be older thn current timestamp +  allow_delta_time\n\n'
			out += f'expect_time_tag        = {self.expect_time_tag}\n'
			out += '                          require time stamp value as first work in message\n\n'
			out += f'use fragments          = {self.use_fragments_to_dermine_device}\n'
			out += '                          allow plugin to try to figure out which device was mean if not 100 % match using fragments\n\n'
			out += f'var_name               = {self.var_name}\n'
			out += '                          name of the variable the plugin will listen to, will be created if it does not exist\n\n'
			out += f'var_name_feedback      = {self.var_name_feedback}\n'
			out += '                          name of the variable the plugin will write reslut to to be pickup by iphone, will be created if it does not exist\n\n'
			out += f'return string if ok    = {self.return_ok}\n'
			out += '                          string written to variable_feedback if execution is ok\n\n'
			out += f'return string if bad   = {self.return_bad}\n'
			out += '                          string written to variable_feedback if execution is not ok\n\n'
			out += f'return silent          = {self.return_silent}\n'
			out += '                          return a blank to iphone \n\n'
			out += f'folder_name            = {self.folder_name}\n'
			out += '                          folder name of the variables, will be created if it does not exist\n\n'
			out += f'blocked_device_words   = {self.blocked_device_words}\n'
			out += '                          words that are not allowed for devices and actions eg "alarm", when they are present the whole command is ignored\n\n'
			out += f'actions                = {self.actions}\n'
			out += '                          indigo action names and indigo ids, using {indigo action name:[indigo action id, seq number]} }\n\n'
			out += f'synonymes for actions  = {self.synonymes_for_actions}\n'
			out += '                           voice action names and  indigo action ids, using {voice action string:indigo action id}  \n\n'
			out += f'synonymes for devices  = {self.synonymes_for_devices}\n'
			out += '                           voice device names and  indigo device ids, using {voice device string:indigo device id}  \n\n'
			out += f'synonymes for variables = {self.synonymes_for_variables}\n'
			out += '                           voice variable names and  indigo variable ids, using {voice variable string:indigo variable id}  \n\n'
			out += f'map_from_to            = {self.map_from_to}\n'
			out += '                           bad words to be replaced by good words  using {map voice string : to string to be used} \n\n'
			out += '                           eg dor : door  \n\n'
			out += '                           or tür : door (for the germans)  \n\n'
			out += f'list devices max       = {self.list_devices_max}\n'
			out += '                           list max number of devices when receiving command list devices \n\n'
			out += '\n'
			self.indiLOG.log(20,out)
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return


	

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
	def writeJson(self, data: dict, fName="", sort=True , doFormat=True, singleLines=False ):
		try:

			if self.decideMyLog("Logic"): self.indiLOG.log(10,"writeJson: fname:{}, sort:{}, doFormat:{}, singleLines:{}, data:{} ".format(fName, sort, doFormat, singleLines, str(data)[0:100]) )
	
			out = ""
			if data == "": return ""
			if data == {} : return ""
			if data is None: return ""

			if doFormat:
				if singleLines:
					out = ""
					for xx in data:
						out += "\n{}:{}".format(xx, data[xx])
				else:
					try: out = json.dumps(data, sort_keys=sort, indent=2)
					except: pass
			else:
					try: out = json.dumps(data, sort_keys=sort)
					except: pass

			if fName !="":
				f = self.openEncoding(fName,"w")
				f.write(out)
				f.close()
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



	###########################	   MAIN LOOP  ############################
	###########################	   MAIN LOOP  ############################
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




	####-----------------	 ---------

	def variableUpdated(self, orig_var: dict, new_var: dict ):
		try:
		
			if self.var_name != orig_var.name: return 
			if self.decideMyLog("ReceivdeData"): self.indiLOG.log(20, f"orig_var '{new_var.value}'")
			if self.return_silent:
				indigo.variable.updateValue(self.var_name_feedback, value=" ")
			else:
				indigo.variable.updateValue(self.var_name_feedback, value=self.return_bad)
				
			raw = new_var.value
	
			if self.decideMyLog("ReceivdeData"):	self.indiLOG.log(20, f"Command received raw: '{raw}'")
	
			if not raw or not raw.strip():
				return
	
			raw_stripped = raw.strip()
	
			ok, raw_stripped = self.check_if_time_tag_ok(raw_stripped)
			if not ok: return 
	
			if self.decideMyLog("ReceivdeData"): self.indiLOG.log(20, f"Command received raw, tags removed: '{raw_stripped}'")
	
			cmd =  self.normalize_command(raw_stripped)
			cmdLower = cmd.lower()
			
			if self.decideMyLog("ReceivdeData"):	self.indiLOG.log(20, f"Normalized command: '{cmd}'")
	
			if cmdLower in["what can you do","list actions"]:
				self.log_available_commands()
				if not self.return_silent:
					indigo.variable.updateValue(self.var_name_feedback, value=self.return_ok)
				return
	
			elif cmdLower == "list devices":
				self.log_devices()
				return
	
			elif cmdLower == "test":
				self.indiLOG.log(20, f"received command: '{cmd}'")
				if not self.return_silent:
					indigo.variable.updateValue(self.var_name_feedback, value=self.return_ok)
				return
	
			elif cmdLower == "debug on":
				self.indiLOG.log(20, f"received command: '{cmd}'")
				self.pluginPrefs["debugAll"] = True
				self.setDebugFromPrefs(self.pluginPrefs)
				if not self.return_silent:
					indigo.variable.updateValue(self.var_name_feedback, value=self.return_ok)
				return

			elif cmdLower == "debug off":
				self.indiLOG.log(20, f"received command: '{cmd}'")
				self.pluginPrefs["debugAll"] = False
				if not self.return_silent:
					indigo.variable.updateValue(self.var_name_feedback, value=self.return_ok)
				self.setDebugFromPrefs(self.pluginPrefs)

			elif cmdLower == "help":
				self.indiLOG.log(20, f"received command: '{cmd}'")
				self.printConfig()
				if not self.return_silent:
					indigo.variable.updateValue(self.var_name_feedback, value=self.return_ok)
				return

			elif cmdLower.find("silence") >-1:
				self.indiLOG.log(20, f"received command: '{cmd}'")
				if cmdLower.find(" on") > 5:
					if not self.return_silent:
						self.return_silent = True
						indigo.variable.updateValue(self.var_name_feedback, value=self.return_ok)
				else:
					self.return_silent = False
					indigo.variable.updateValue(self.var_name_feedback, value=self.return_ok)
				return
	
	
			# Compound support: run each sub-command in order
			sub_cmds =  self.split_compound(cmd)
			if len(sub_cmds) > 1:
					if self.decideMyLog("all"):	self.indiLOG.log(20, f"Compound command -> {sub_cmds}")
					for sub in sub_cmds:
						 self.execute_actions_for_command(sub)
			else:
					self.execute_actions_for_command(cmd)
	

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return False



	def apply_PhraseMappings(self, text: str) -> str:
		if not text:
			return text
		out = copy.copy(text)
		for bad, good in self.map_from_to.items():
			out = re.sub(rf"\b{re.escape(bad)}\b", good, out)
		return out



	def is_blocked_device_name(self, name: str) -> bool:
		if not name:
			return False
		nameL = name.lower()	
		for test in  self.blocked_device_words:
			if test in nameL: return True
			
		return False
	
	def normalize_name_for_match(self, s: str) -> str:
		if s is None:
			return ""
		s = s.lower()

		# lamp/light equivalence (pattern-derived device matching uses this)
		for bad in self.map_from_to:
			if bad in s:
				s = s.replace()
			#s = re.sub(r"\""+toBeReplaced+"\b", self.REPLACE_STRINGS_WITH[toBeReplaced], s) # replace lamp with light .. etc

		s = re.sub(r"[\/_\-]", " ", s) # replace / _ - with one blank 
		s = re.sub(r"\s+", " ", s) # replace multiple white spaces with one blank 
		return s.strip()
	
	
	def check_if_time_tag_ok(self, test: str) -> (bool, str):
		messageTime = test.split()[0].lower()
		if not  self.expect_time_tag:
			# remove time since epoch tag if present 
			try: 
				float(messageTime)
				test = test[len(messageTime)+1:]
			except: pass
			return True, test
				
		try:
				messageTimeNumber = float(messageTime)
		except:
			if self.decideMyLog("BadMessage"):	self.indiLOG.log(20, f"Ignoring '{test}'; bad time info, not a number")
			return
		
		dt = time.time() - messageTimeNumber
		if dt >  self.allow_delta_time:
			if self.decideMyLog("BadMessage"):	self.indiLOG.log(20, f"Ignoring '{test}'; time not in allowed window: {dt:.1f}")
			return False, ""
			
		if self.decideMyLog("Logic"):self.indiLOG.log(20, f"accepted  '{test}'; time in allowed window: {dt:.1f}")
		
		return True, test[len(messageTime):].strip()
	
	def normalize_command(self, raw: str) -> str:
		if raw is None:
				return ""
		text = raw.strip().lower()
		text = text.strip(" .!?") 
		text = re.sub(r"\s+", " ", text).strip()# replace multiple white spaces with one blank and no blank at the end
		text =  self.apply_PhraseMappings(text)
		text = re.sub(r"\s+", " ", text).strip()# replace multiple white spaces with one blank and no blank at the end
		return text
	
	def normalize_device_phrase(self, phrase: str) -> str:
		"""Used only for pattern-parsed device phrases (set/turn on/off)."""
		if not phrase:
			return ""
		p = phrase.strip().lower()
		p = re.sub(r"^(?:the\s+)+", "", p) # replace the with nothing
		p = re.sub(r"^(?:hue\s+)+", "", p) # replace hue with nothing 
		p = re.sub(r"\s+", " ", p).strip() # replace multiple white spaces with one blank and no blank at the end
		p =  self.apply_PhraseMappings(p)
		p = re.sub(r"\s+", " ", p).strip() # replace multiple white spaces with one blank and no blank at the end
		return p
	
	def tokens(self, s: str):
		s =  self.normalize_name_for_match(s)
		if not s:
			return []
		return [t for t in s.split(" ") if t]
	
	def find_device_by_name_fragment(self, fragment: str):
	
		# if we have perfect match we dont need to loop though all devices to find a match twice
		if not  self.is_blocked_device_name(fragment):
			if fragment in indigo.devices:
				if self.decideMyLog("Logic"): self.indiLOG.log(20, f"find_device_by_name_fragment: use perfect match device: '{fragment}'")
				return indigo.devices[fragment]

		if not self.use_fragments_to_dermine_device: return None
		
		
		frag_norm =  self.normalize_name_for_match(fragment)
		if not frag_norm:
			return None

		# 1) exact / substring (but skip blocked devices)
		exact_matches = []
		partial_matches = []
		blocked_candidates = []

		
		for dev in indigo.devices:
			# Block ONLY pattern-derived device control
			if  self.is_blocked_device_name(dev.name):
				# Track if it would have matched, for logging
				dev_norm =  self.normalize_name_for_match(dev.name)
				if dev_norm == frag_norm or frag_norm in dev_norm:
					blocked_candidates.append(dev)
				continue

			dev_norm =  self.normalize_name_for_match(dev.name)
			if dev_norm == frag_norm:
				exact_matches.append(dev)
			elif frag_norm in dev_norm:
				partial_matches.append(dev)

		candidates = exact_matches or partial_matches
		if candidates:
			if len(candidates) > 1:
				names = ", ".join(d.name for d in candidates[:20])
				suffix = "" if len(candidates) <= 20 else f" (+{len(candidates)-20} more)"
				if self.decideMyLog("Logic"): self.indiLOG.log(20, f"multiple devices match '{fragment}': {names}{suffix}")
			return candidates[0]

		# If we only matched blocked devices, say why
		if blocked_candidates:
			names = ", ".join(d.name for d in blocked_candidates[:10])
			suffix = "" if len(blocked_candidates) <= 10 else f" (+{len(blocked_candidates)-10} more)"
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"Blocked pattern device control for '{fragment}' (matches blocked device name): {names}{suffix}")
			return None

		# 2) token-subset match (skip blocked devices)
		frag_tokens = set(tokens(frag_norm))
		if not frag_tokens:
			return None

		scored = []
		blocked_token_matches = []

		for dev in indigo.devices:
			if is_blocked_device_name(dev.name):
				dev_tokens = set(self.tokens(dev.name))
				if frag_tokens.issubset(dev_tokens):
					blocked_token_matches.append(dev)
				continue

			dev_tokens = set(self.tokens(dev.name))
			if frag_tokens.issubset(dev_tokens):
				extra = len(dev_tokens) - len(frag_tokens)
				scored.append((extra, len(dev.name), dev))

		if scored:
			scored.sort(key=lambda x: (x[0], x[1]))
			best = scored[0][2]

			if len(scored) > 1:
				top = [d.name for _, _, d in scored[:10]]
				if self.decideMyLog("Logic"): self.indiLOG.log(20, f"token match for '{fragment}' -> using '{best.name}' (also: {', '.join(top[1:])})")
			return best

		if blocked_token_matches:
			names = ", ".join(d.name for d in blocked_token_matches[:10])
			suffix = "" if len(blocked_token_matches) <= 10 else f" (+{len(blocked_token_matches)-10} more)"
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"Blocked pattern device control for '{fragment}' (token match hits blocked device): {names}{suffix}")
			return None

		return None

	
	
	# ==========================
	#  META COMMANDS
	# ==========================
	
	def log_available_commands(self):
		self.indiLOG.log(20,"Available ACTION commands: that are mapped from voice to actual indigo action groups")
		for cmd in sorted( self.actions.keys()):
			self.indiLOG.log(20, f"  {cmd}")
	
	def log_devices(self):
		self.indiLOG.log(20,"Device list (name → normalized) [truncated if large]:")
		count = 0
		for dev in indigo.devices:
			if count >=  self.list_devices_max:
				self.indiLOG.log(20, f"... truncated at {self.list_devices_max} devices ...")
				break
			self.indiLOG.log(20, f"   {dev.name:55} → {self.normalize_name_for_match(dev.name)}")
			count += 1
	
	
	# ==========================
	#  device/ var EXECUTION
	# ==========================

	# utils 	
	def device_is_dimmable(self, dev) -> bool:
		try:
			return ("brightnessLevel" in dev.states) or ("dimLevel" in dev.states)
		except Exception:
			return False
	
	def check_if_match_devices(self, theName: str):
		
		if self.decideMyLog("Logic"):	self.indiLOG.log(20, f"check_if_match_device  theName {theName}")

		if theName in indigo.devices:
			return indigo.devices[theName]

		theName = self.synonymes_for_devices.get(theName, theName)
		try: 
			id = int(theName)
			if self.decideMyLog("Logic"):	self.indiLOG.log(20, f"check_if_match_devices  id  {theName},  in indigo?:{id in indigo.devices}")
		except: return None
		 
		try:
			xxx = indigo.devices[int(id)]
			return xxx
		except: pass
		return  None

	def check_if_match_variables(self, theName):
		if self.decideMyLog("Logic"):	self.indiLOG.log(20, f"check_if_match_variables  theName {theName}")
		if theName in indigo.variables:
			return indigo.variables[theName]

		
		theName = self.synonymes_for_variables.get(theName, theName)
		try: 
			id = int(theName)
			if self.decideMyLog("Logic"):	self.indiLOG.log(20, f"check_if_match_variables  id  {theName},  in indigo?:{id in indigo.variables}")
		except: return None
		 
		try:
			xxx = indigo.variables[int(id)]
			return xxx
		except: pass
		return  None

	# handle updates


	def handle_set_speed(self, cmd: str) -> bool:
		
		#  cmd:  (set) speed device to xx
		pos = cmd.find("speed ")
		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_speed '{cmd}' speed at pos {pos}")
		if pos < 0: return False
		cmd = cmd.split("speed ")[1]

		pos = cmd.find(" to ")
		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_speed '{cmd}' to at pos {pos}")
		if pos < 5: return False
		theName, speed = cmd.split(" to ")
		dev = self.check_if_match_devices(theName)
		if not dev:
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"No device found matching '{theName}'")
			return False
		if "speedLevel" not in dev.states: 
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"No device '{theName}' does not have speed control")
			return False
		
		# map speed to a number 
		if speed in _mapNumbertextToInt:
			speed = _mapNumbertextToInt[speed]
		else:
			try: speed = int(speed)
			except: pass

		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_speed found '{theName}' {speed}")
			
		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_speed '{dev.name}' speed {speed}")
		indigo.speedcontrol.setSpeedIndex(dev.id, value=speed)
		return True

	
	# handle updates
	def handle_set_level(self, cmd: str) -> bool:
		

		pos = cmd.find("bright")
		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_level '{cmd}' bright at pos {pos}")
		if pos < 0: return False
		cmd = cmd.strip("%")
		cmd = cmd.strip(" ")
		pos = cmd.find(" ")
		cmd = cmd[pos+1:].strip()
		pos = cmd.find("level ")
		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_level '{cmd}' level at pos {pos}")
		if pos == 0: #remove " level "
			cmd = cmd[len("level "):].strip()
		
		cmd1 = cmd.split(" to ")
		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_level to '{cmd}'")
		if len(cmd1) == 2:
			phrase = cmd1[0]
			level = cmd1[1].strip()
		else:
			pos = cmd.rfind(" ")
			level = cmd[pos+1:].strip()
			phrase = cmd[:pos].strip()
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_level rfind '{pos}'")

		level = level.strip("%")
		level = level.strip("percent")
		if level in _mapNumbertextToInt:
			level = _mapNumbertextToInt[level]
		else:
			try: level = int(level)
			except: pass

		if self.decideMyLog("Logic"):	self.indiLOG.log(20, f"handle_set_level1  dev {phrase}, level:{level}%")
		dev = self.check_if_match_devices(phrase)
		if not dev:
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"No device found matching '{phrase}'")
			return False

		level = max(0, min(100, int(level)))

		if self.device_is_dimmable(dev):
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"Setting dev '{dev.name}' to {level}%")
			try:
				indigo.dimmer.setBrightness(dev.id, value=level)
				if not self.return_silent:
					indigo.variable.updateValue(self.var_name_feedback, value=self.return_ok)
			except	Exception as e:
				if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
				return False
			return True

		# relay fallback: >0 => ON, 0 => OFF
		if level == 0:
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"Setting dev '{dev.name}' to 0% (relay -> OFF)")
			try:
				indigo.device.turnOff(dev.id)
				if not self.return_silent:
					indigo.variable.updateValue(self.var_name_feedback, value=self.return_ok)
			except Exception as e:
				self.indiLOG.log(20, f"Error turning off '{dev.name}': {e}")
		else:
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"Setting dev '{dev.name}' to {level}% (relay -> ON)")
			try:
				indigo.device.turnOn(dev.id)
				if not self.return_silent:
					indigo.variable.updateValue(self.var_name_feedback, value=self.return_ok)
			except	Exception as e:
				if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
				return False
			return True

		return False


	
	def handle_unlock(self, cmd: str) -> bool:
	
		pos = cmd.find("unlock ")
		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_unlock '{cmd}'  unlock at pos {pos}")
		if pos < 0: return False
		cmd = cmd.split("unlock ")[1]


		dev = self.check_if_match_devices(phrase)
		if not dev:
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"No device found matching '{phrase}'")
			return False

		if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"unlock dev '{dev.name}'")
		indigo.device.unlock(dev.id)
		if not self.return_silent:
			indigo.variable.updateValue(self.var_name_feedback, value=self.return_ok)
		return True

	
	def handle_lock(self, cmd: str) -> bool:
	
		pos = cmd.find("lock ")
		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_lock '{cmd}'  lock at pos {pos}")
		if pos < 0: return False
		cmd = cmd.split("lock ")[1]


		dev = self.check_if_match_devices(phrase)
		if not dev:
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"No device found matching '{phrase}'")
			return False

		if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"lock dev '{dev.name}'")
		indigo.device.lock(dev.id)
		if not self.return_silent:
			indigo.variable.updateValue(self.var_name_feedback, value=self.return_ok)
		return True
			
	
	def handle_beep(self, cmd: str) -> bool:
	
		pos = cmd.find("beep ")
		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_beep '{cmd}'  beep at pos {pos}")
		if pos < 0: return False
		cmd = cmd.split("beep ")[1]


		dev = self.check_if_match_devices(phrase)
		if not dev:
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"No device found matching '{phrase}'")
			return False

		if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"beep dev '{dev.name}'")
		indigo.device.beep(dev.id)
		if not self.return_silent:
			indigo.variable.updateValue(self.var_name_feedback, value=self.return_ok)
		return True
	
	
	def handle_turn_on_off(self, cmd: str) -> bool:
	
		pos = cmd.find("turn")
		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_lock '{cmd}'  turn at pos {pos}")
		if pos != 0: return False
		cmd = cmd[pos+4:].strip()
		state = cmd.split()[0]
		phrase = cmd[len(state)+1:].strip()
		
		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_turn_on_off dev {phrase}, state {state}")

		dev = self.check_if_match_devices(phrase)
		if not dev:
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"No device found matching '{phrase}'")
			return False

		if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"Turning dev '{dev.name}' to  {state}")

		try:
			if state == "on":
				if self.device_is_dimmable(dev):
					indigo.dimmer.setBrightness(dev.id, value=100)
				else:
					indigo.device.turnOn(dev.id)
			else:
				if self.device_is_dimmable(dev):
					indigo.dimmer.setBrightness(dev.id, value=0)
				else:
					indigo.device.turnOff(dev.id)
			if not self.return_silent:
				indigo.variable.updateValue(self.var_name_feedback, value=self.return_ok)
			return True
			
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
			
		return False
	
	
	def handle_toggle(self, cmd: str) -> bool:
	
		m = re.match(r"^toggle\s+(?:the\s+)?(.+)$", cmd)
		if not m: return False
		
		if self.decideMyLog("Logic"):	self.indiLOG.log(20, f"handle_toggle  m:{m.groups()}")
		phrase = m.group(1)
		dev = self.check_if_match_devices(phrase)
		if not dev:
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"No device found matching '{phrase}'")
			return False

		if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"toggle dev '{dev.name}'")

		try:
			indigo.device.toggle(dev.id)
			if not self.return_silent:
				indigo.variable.updateValue(self.var_name_feedback, value=self.return_ok)
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		return True

	
	def handle_set_heat(self, cmd: str) -> bool:
	
		pos = cmd.find("heat ")
		if pos >= 0:
			rest = cmd.split("heat ")[1]

		if pos < 0: return False
		m = rest.split(" to ")
		if len(m) != 2: return False
				
		phrase = m[0]
		level = int( m[1].split(" ")[0] )  

		if self.decideMyLog("Logic"):	self.indiLOG.log(20, f"handle_set_heat  m:{m}")
		dev = self.check_if_match_devices(phrase)
		if not dev:
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"No device found matching '{phrase}'")
			return False

		if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_set_heat dev '{dev.name}' to {level} º")

		try:
			indigo.thermostat.setHeatSetpoint(dev.id, value=int(level))
			if not self.return_silent:
				indigo.variable.updateValue(self.var_name_feedback, value=self.return_ok)
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
			return False

		return True
	
	
	def handle_set_cool(self, cmd: str) -> bool:
	
		pos = cmd.find("cool ")
		if pos >= 0:
			rest = cmd.split("cool ")[1]
		
		if pos < 0: return False

		m = rest.split(" to ")
		if len(m) != 2: return False

		phrase = m[0]
		level = int( m[1].split(" ")[0] )  
	
		if self.decideMyLog("Logic"):	self.indiLOG.log(20, f"handle_set_cool m:{m}")
		dev = self.check_if_match_devices(phrase)
		if not dev:
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"No device found matching '{phrase}'")
			return False

		if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_set_cool dev '{dev.name}' to {level} º")

		try:
			indigo.thermostat.setCoolSetpoint(dev.id, value=int(level))
			if not self.return_silent:
				indigo.variable.updateValue(self.var_name_feedback, value=self.return_ok)
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		return True
	
	
	def handle_set_variable(self, cmd: str) -> bool:
	
		pos = cmd.find("set variable ")
		if pos < 0: return False
		rest = cmd.split("set variable ")[1]
		if " to " not in rest: return  False
		phrase , value = rest.split(" to ")
		numbers = re.findall("\d+", value)
		
		if self.decideMyLog("Logic"):	self.indiLOG.log(20, f"handle_set_variable   variable:{phrase}  to {value}")
		var = self.check_if_match_variables(phrase)
		if not var:
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"No Variable found matching '{phrase}'")
			return False

		if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"update var '{var.name}' to {value}")

		try:
			indigo.variable.updateValue(var.name, value=value)
			if not self.return_silent:
				indigo.variable.updateValue(self.var_name_feedback, value=self.return_ok)
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
			return False

		return True


	
	def handle_get_value(self, cmd: str) -> bool:
		#  command :=  get device xx state yy 
		#  command :=  get variable xx 
		pos = cmd.find("get ")
		if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_get_value var '{cmd}' pos {pos}")
		if pos != 0: return False

		cmd = cmd.split("get ")[1]

		pos = cmd.find("variable ")
		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_get_value var '{cmd}' pos {pos}")
		if pos == 0: 
			cmd = cmd.split("variable ")[1]
			var = self.check_if_match_variables(cmd)
			if not var:  return False
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_get_value var '{var.name}' value:{var.value}")
			indigo.variable.updateValue(self.var_name_feedback, value=var.value)
			return True
			
		# check devices
		pos = cmd.find(" state ")
		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_get_value dev '{cmd}' pos {pos}")
		if pos > 5: 
			xx = cmd.split(" state ")
			if len(xx) < 2: return False
			devName, state = cmd.split(" state ")
			dev = self.check_if_match_devices(devName)
			if not dev: return False
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_get_value dev '{devName}' {dev.name} ")
			if state not in dev.states: return False
			value = str(dev.states[state])
			indigo.variable.updateValue(self.var_name_feedback, value=value)
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_get_value  {dev.name}  state:{value}")

			return True

		return False


	def try_pattern_commands(self, cmd: str) -> bool:
		try:
			state = "none"
			cmd = re.sub(r"\s+", " ", cmd.strip())
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands {cmd} ")

			###get variable or device / state value  ##
			if self.handle_get_value(cmd): return  True

			### variables  first must have "set variable name to xx "
			if self.handle_set_variable(cmd): return  True

			### devices ##
			if self.handle_set_speed(cmd): return True

			if self.handle_beep(cmd): return True

			if self.handle_lock(cmd): return True
			
			if self.handle_unlock(cmd): return True
			
			if self.handle_turn_on_off(cmd): return True
	
			if self.handle_toggle(cmd): return  True

			if self.handle_set_heat(cmd): return  True

			if self.handle_set_cool(cmd): return  True

			if self.handle_set_level(cmd): return  True


			if not self.return_silent:
				indigo.variable.updateValue(self.var_name_feedback, value=self.return_bad)

			return False
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		if not self.return_silent:
			indigo.variable.updateValue(self.var_name_feedback, value=self.return_bad)
	
	def execute_actions_for_command(self, cmd: str):
	
		isSynonym = self.synonymes_for_actions.get(cmd, 0)
		actionInfo = False
		if self.decideMyLog("logic"): self.indiLOG.log(20, f"execute_actions_for_command '{cmd}' isSynonym:{isSynonym}")

		if isSynonym != 0:
			for action in self.actions:
				if isSynonym == self.actions[action][0]: # == indigo id
					actionInfo = self.actions[action]
					break
					
		if not actionInfo:
			actionInfo = self.actions.get(cmd, False)
			
		if not actionInfo:
			if self.try_pattern_commands(cmd):
				return
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"No match for '{cmd}' in ACTIONs or patterns")
			return

		if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"Matched command '{cmd}' → action groups {actionInfo}")
		try:
			indigo.actionGroup.execute(actionInfo[0])
			if not self.return_silent:
				indigo.variable.updateValue(self.var_name_feedback, value=self.return_ok)
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
	
	
	# ==========================
	#  COMPOUND COMMANDS
	# ==========================
	
	def split_compound(self, cmd: str):
		"""
		Split on 'and' / 'then' / '&' with spaces.
		Example: 'unmute tv and set tv to 24' -> ['unmute tv', 'set tv to 24']
		"""
		if not cmd:
			return []
		parts = re.split(r"\s+(?:and|then|&)\s+", cmd, flags=re.IGNORECASE)
		return [p.strip() for p in parts if p and p.strip()]
	





	####-----------------	 ---------
	def decideMyLog(self, msgLevel: int):
		try:
			if msgLevel	 == "All" or "All" in self.debugAreas:		return True
			if msgLevel	 == ""  and "All" not in self.debugAreas:	return False
			if msgLevel in self.debugAreas:							return True

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return False
#
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


