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
_mapNumbertextToInt = {	"zero":0, "null":0, 			"one":1,  "two":2,  "three":3, "four":4, "five":5, 				"six":6,  	"seven":7,  "eight":8,	"nine":9, "ten":10,	"	eleven":11,"twelve":11,				#	english
						          "null":0, 			"eins":1, "zwei":2, "drei":3,  "vier":4, "fünf":5, "fuenf":5, 	"sechs":6,	"sieben":7, "acht":8, 	"neun":9, "zehn":10,	"elf":11,  "zwölf":12, "zwoelf":12,#	german
						          "nulo":0, 			"cero":1, "dos":2, "tres":3,  "cuatro":4, "cinco":5, 		 	"seis":6,	"siete":7,	"ocho":8, 	"nueve":9, "diez":10,	"once":11,  "doce":12,				#	spanish
						"nulle":0, "zero":0, "zéro":0,	"un":1,   "deux":2, "trois":3, "quatre":4, "cinq":5, 			"six":6,	"sept":7, 	"huit":8, 	"neuf":9, "dix":10, 	"onze":11, "douze":12}				#	french


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
	"of":									"of",
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
	"dip":									"dip",
	"variable":								"variable",
	"plainactionCommand":					True,

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
	"ok-dip":								"dipped",
	"ok-action":							"action",

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
		"""Constructor for the plugin; calls the Indigo PluginBase initializer and sets up core attributes such as plugin paths, IDs, PID, macOS user info, logging handlers/formatters with per-level formats, and the Python interpreter path. Logs environment and version details on startup.

		Inputs:
		    pluginId (str): Indigo plugin identifier
		    pluginDisplayName (str): human-readable plugin name
		    pluginVersion (str): plugin version string
		    pluginPrefs (indigo.Dict): persisted plugin preferences
		Outputs:
		    None: initializes instance attributes and logging
		"""
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
		"""Destructor that delegates to the Indigo PluginBase __del__ for cleanup.

		Inputs:
		    None.
		Outputs:
		    None: delegates teardown to PluginBase
		"""
		indigo.PluginBase.__del__(self)

	###########################		INIT	## START ########################

	####----------------- @ startup set global parameters, create directories etc ---------
	def startup(self):

		"""Indigo startup hook that resets quit state, verifies the plugin name (exiting if invalid), records the start time, flags variables for re-initialization, and applies debug settings from preferences.

		Inputs:
		    None.
		Outputs:
		    None: sets startup state and applies debug prefs
		"""
		self.quitNOW = ""

		if not checkIndigoPluginName(self, indigo):
			exit()
			
		self.pluginStartTime = time.time()
		self.redoInitVariables = True
		self.setDebugFromPrefs(self.pluginPrefs, writeToLog=False)
		
		return


	####-----------------	 ---------
	def initVariables(self):
		"""Initializes the plugin's working variables from preferences and JSON files: ensures the preferences directory exists, builds action-word translation and feedback maps, loads synonym/mapping/blocked-word/command-history dictionaries, reads various tuning preferences, and creates the configured Indigo variable folder and variables.

		Inputs:
		    None.
		Outputs:
		    None: populates instance config attributes and creates Indigo variables/folders; logs errors
		"""
		try:
			self.redoInitVariables = False

			if not os.path.exists(self.indigoPreferencesPluginDir):
				os.mkdir(self.indigoPreferencesPluginDir)
			if not os.path.exists(self.indigoPreferencesPluginDir):
				self.indiLOG.log(50,"error creating the plugin data dir did not work, can not create: {}".format(self.indigoPreferencesPluginDir)  )
				self.sleep(1000)
				exit()
				
			self.action_words = ["set", "get", "to", "of", "level", "bright", "toggle", "pulse", "dip", "turn", "on", "off", "speed", "beep", "cool", "heat", "lock", "unlock", "silence", "variable", "wait"]

			self.translate = {}
			for xx in self.action_words:
				self.translate[xx] = self.pluginPrefs.get(xx, kDefaultPluginPrefs[xx])

			self.feedback_ok = {}
			for xx in ["set", "get", "bright", "toggle", "pulse", "dip", "turn", "speed", "beep", "cool", "heat", "lock", "unlock", "silence", "wait", "action"]:
				self.feedback_ok[xx] = self.pluginPrefs.get("ok-"+xx, kDefaultPluginPrefs["ok-"+xx])


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
		"""Returns the config UI values for a menu action; for the 'blockedWords' menu it injects the current blocked words joined by '|' into the dialog values.

		Inputs:
		    menuId (str): identifier of the menu being opened
		Outputs:
		    dict: config UI values for the menu dialog
		"""
		xx =  super(Plugin, self).getMenuActionConfigUiValues(menuId)
		if menuId == "blockedWords":
			yy = "|".join(self.blocked_words)
			xx[0]["blocked_words"] = yy
		return xx
		
	####-----------------  ---------
	#### good bad words 
	####-----------------  ---------
	def blockWordsCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20, f"blockWordsCallback {valuesDict}")
		"""Callback that parses the '|'-delimited blocked-words string from the dialog into a cleaned list and persists it to blocked_words.json.

		Inputs:
		    valuesDict (indigo.Dict or None): dialog values containing blocked_words
		    typeId (str): config UI type identifier
		Outputs:
		    None: updates self.blocked_words and writes JSON file
		"""
		yy = valuesDict["blocked_words"].split("|")
		self.blocked_words= []
		for xx in yy:
			if xx.strip() != "":
				self.blocked_words.append(xx.strip())
		self.writeJson(self.blocked_words, fName=self.indigoPreferencesPluginDir + "blocked_words.json", sort = True, doFormat=True, singleLines= False )



	####-------------------------------------------------------------------------####
	def filterFromTo(self, filter="", valuesDict=None , typeId=None):
		"""List filter callback that builds menu entries from the from-to mapping, returning each key alongside a 'key->value' display label.

		Inputs:
		    filter (str): filter string from the UI
		    valuesDict (indigo.Dict or None): current dialog values
		    typeId (str or None): config UI type identifier
		Outputs:
		    list: list of [key, label] pairs for the from-to map
		"""
		xList = []
	
		for syn in self.map_from_to:
			xList.append([syn, syn+"->"+self.map_from_to[syn]])
		#self.indiLOG.log(20, f"filterSynonymes xList: {xList}")
		return xList


	####-----------------  ---------
	def addFromCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20, f"selectActionsCallback {valuesDict}")
		"""Callback that adds a new from->to mapping entry from the dialog's 'from' and 'to' fields (if not already present) and persists the map to map_from_to.json.

		Inputs:
		    valuesDict (indigo.Dict or None): dialog values with 'from' and 'to'
		    typeId (str): config UI type identifier
		Outputs:
		    None: updates self.map_from_to and writes JSON file
		"""
		bad = valuesDict["from"]
		good = valuesDict["to"]
		if bad not in self.map_from_to:
			self.map_from_to[bad] = good
		self.writeJson(self.map_from_to, fName=self.indigoPreferencesPluginDir + "map_from_to.json", sort = True, doFormat=True, singleLines= False )


	####-----------------  ---------
	def removeFromCallback(self, valuesDict=None , typeId=""):
		"""Callback that removes the from->to mapping entry named by the dialog's 'fromRemove' field and persists the updated map to map_from_to.json.

		Inputs:
		    valuesDict (indigo.Dict or None): dialog values with 'fromRemove'
		    typeId (str): config UI type identifier
		Outputs:
		    None: removes entry from self.map_from_to and writes JSON file; logs
		"""
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
		"""List filter callback that, when the filter is 'synonymes', returns the plugin's Indigo action groups as [id, name] pairs for selection.

		Inputs:
		    filter (str): filter string; 'synonymes' enables listing
		    valuesDict (indigo.Dict or None): current dialog values
		    typeId (str or None): config UI type identifier
		Outputs:
		    list: list of [actionGroupId, name] pairs
		"""
		xList = []
		if filter  == "synonymes":
			for action in indigo.actionGroups.iter(self.pluginId):
				xList.append([action.id, action.name])

		#self.indiLOG.log(20, f"filterActions xList: {xList}")
		return xList


####-------------------------------------------------------------------------####
	def filterSynonymesActions(self, filter="", valuesDict=None , typeId=None):
		"""List filter callback that returns the currently defined action synonyms as [synonym, synonym] pairs for the UI.

		Inputs:
		    filter (str): filter string from the UI
		    valuesDict (indigo.Dict or None): current dialog values
		    typeId (str or None): config UI type identifier
		Outputs:
		    list: list of [synonym, synonym] pairs
		"""
		xList = []
	
		for syn in self.synonymes_for_actions:
			xList.append([syn, syn])
		#self.indiLOG.log(20, f"filterSynonymes xList: {xList}")
		return xList


	####-------------------------------------------------------------------------####
	def addSynonymActionCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20, f"selectActionsCallback {valuesDict}")
		"""Callback that maps a new action synonym (from the dialog's 'add' field) to the selected action id (if not already present) and persists the synonyms to synonymes_for_actions.json.

		Inputs:
		    valuesDict (indigo.Dict or None): dialog values with 'id' and 'add'
		    typeId (str): config UI type identifier
		Outputs:
		    None: updates self.synonymes_for_actions and writes JSON file
		"""
		id = valuesDict["id"]
		synonym = valuesDict["add"]
		if synonym not in self.synonymes_for_actions:
			self.synonymes_for_actions[synonym] = id
		self.writeJson(self.synonymes_for_actions, fName=self.indigoPreferencesPluginDir + "synonymes_for_actions.json", sort = True, doFormat=True, singleLines= False )


	####-----------------  ---------
	def removeSynonymActionCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20, f"selectActionsCallback {valuesDict}")
		"""Removes the action synonym named in valuesDict['remove'] from the synonymes_for_actions dictionary and persists the updated mapping to its JSON file.

		Inputs:
		    valuesDict (dict or None): config UI values containing the 'remove' key with the synonym to delete
		    typeId (str): Indigo config UI type identifier
		Outputs:
		    None: deletes synonym entry and writes synonymes_for_actions.json
		"""
		synonym = valuesDict["remove"]
		if synonym in self.synonymes_for_actions:
			del self.synonymes_for_actions[synonym]
		self.writeJson(self.synonymes_for_actions, fName=self.indigoPreferencesPluginDir + "synonymes_for_actions.json", sort = True, doFormat=True, singleLines= False )


	####-----------------  ---------
	#### define synonymes for devices
	####-----------------  ---------
	def filterDevices(self, filter="", valuesDict=None , typeId=None):
		# also used to enable and disable actions 
		"""Builds a selection list of all Indigo devices as [id, name] pairs for use in a config UI menu list.

		Inputs:
		    filter (str): Indigo list filter string (unused)
		    valuesDict (dict or None): current config UI values (unused)
		    typeId (str or None): Indigo config UI type identifier (unused)
		Outputs:
		    list: list of [device id, device name] pairs for all Indigo devices
		"""
		xList = []
	
		for dev in indigo.devices.iter():
			xList.append([dev.id, dev.name])
			continue
							
		#self.indiLOG.log(20, f"filterActions xList: {xList}")
		return xList


	####-------------------------------------------------------------------------####
	def filterSynonymesDevices(self, filter="", valuesDict=None , typeId=None):
		"""Builds a selection list of the currently defined device synonym phrases as [synonym, synonym] pairs for a config UI menu list.

		Inputs:
		    filter (str): Indigo list filter string (unused)
		    valuesDict (dict or None): current config UI values (unused)
		    typeId (str or None): Indigo config UI type identifier (unused)
		Outputs:
		    list: list of [synonym, synonym] pairs from synonymes_for_devices
		"""
		xList = []
		for syn in self.synonymes_for_devices:
			xList.append([syn, syn])
		#self.indiLOG.log(20, f"filterSynonymes xList: {xList}")
		return xList


	####-------------------------------------------------------------------------####
	def addSynonymDeviceCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20, f"selectActionsCallback {valuesDict}")
		"""Adds a new device synonym (valuesDict['add']) mapped to a device id (valuesDict['id']) into synonymes_for_devices if not already present, then persists the mapping to its JSON file.

		Inputs:
		    valuesDict (dict or None): config UI values containing 'id' (device id) and 'add' (synonym phrase)
		    typeId (str): Indigo config UI type identifier
		Outputs:
		    None: adds synonym entry and writes synonymes_for_devices.json
		"""
		id = valuesDict["id"]
		synonym = valuesDict["add"]
		if synonym not in self.synonymes_for_devices:
			self.synonymes_for_devices[synonym] = id
		self.writeJson(self.synonymes_for_devices, fName=self.indigoPreferencesPluginDir + "synonymes_for_devices.json", sort = True, doFormat=True, singleLines= False )


	####-----------------  ---------
	def removeSynonymDeviceCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20, f"selectActionsCallback {valuesDict}")
		"""Removes the device synonym named in valuesDict['remove'] from synonymes_for_devices and persists the updated mapping to its JSON file.

		Inputs:
		    valuesDict (dict or None): config UI values containing the 'remove' key with the synonym to delete
		    typeId (str): Indigo config UI type identifier
		Outputs:
		    None: deletes synonym entry and writes synonymes_for_devices.json
		"""
		synonym = valuesDict["remove"]
		if synonym in self.synonymes_for_devices:
			del self.synonymes_for_devices[synonym]
		self.writeJson(self.synonymes_for_devices, fName=self.indigoPreferencesPluginDir + "synonymes_for_devices.json", sort = True, doFormat=True, singleLines= False )


	####-----------------  ---------
	#### define synonymes for variables
	####-----------------  ---------
	def filterVariables(self, filter="", valuesDict=None , typeId=None):
		# also used to enable and disable actions 
		"""Builds a selection list of all Indigo variables as [id, name] pairs for use in a config UI menu list.

		Inputs:
		    filter (str): Indigo list filter string (unused)
		    valuesDict (dict or None): current config UI values (unused)
		    typeId (str or None): Indigo config UI type identifier (unused)
		Outputs:
		    list: list of [variable id, variable name] pairs for all Indigo variables
		"""
		xList = []
	
		for var in indigo.variables.iter():
			xList.append([var.id, var.name])
			continue
							
		#self.indiLOG.log(20, f"filterActions xList: {xList}")
		return xList


	####-------------------------------------------------------------------------####
	def filterSynonymesVariables(self, filter="", valuesDict=None , typeId=None):
		"""Builds a selection list of the currently defined variable synonym phrases as [synonym, synonym] pairs for a config UI menu list.

		Inputs:
		    filter (str): Indigo list filter string (unused)
		    valuesDict (dict or None): current config UI values (unused)
		    typeId (str or None): Indigo config UI type identifier (unused)
		Outputs:
		    list: list of [synonym, synonym] pairs from synonymes_for_variables
		"""
		xList = []
	
		for syn in self.synonymes_for_variables:
			xList.append([syn, syn])
		#self.indiLOG.log(20, f"filterSynonymes xList: {xList}")
		return xList


	####-------------------------------------------------------------------------####
	def addSynonymVariableCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20, f"selectActionsCallback {valuesDict}")
		"""Adds a new variable synonym (valuesDict['add']) mapped to a variable id (valuesDict['id']) into synonymes_for_variables if not already present, then persists the mapping to its JSON file.

		Inputs:
		    valuesDict (dict or None): config UI values containing 'id' (variable id) and 'add' (synonym phrase)
		    typeId (str): Indigo config UI type identifier
		Outputs:
		    None: adds synonym entry and writes synonymes_for_variables.json
		"""
		id = valuesDict["id"]
		synonym = valuesDict["add"]
		if synonym not in self.synonymes_for_variables:
			self.synonymes_for_variables[synonym] = id
		self.writeJson(self.synonymes_for_variables, fName=self.indigoPreferencesPluginDir + "synonymes_for_variables.json", sort = True, doFormat=True, singleLines= False )


	####-----------------  ---------
	def removeSynonymVariableCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20, f"selectActionsCallback {valuesDict}")
		"""Removes the variable synonym named in valuesDict['remove'] from synonymes_for_variables and persists the updated mapping to its JSON file.

		Inputs:
		    valuesDict (dict or None): config UI values containing the 'remove' key with the synonym to delete
		    typeId (str): Indigo config UI type identifier
		Outputs:
		    None: deletes synonym entry and writes synonymes_for_variables.json
		"""
		synonym = valuesDict["remove"]
		if synonym in self.synonymes_for_variables:
			del self.synonymes_for_variables[synonym]
		self.writeJson(self.synonymes_for_variables, fName=self.indigoPreferencesPluginDir + "synonymes_for_variables.json", sort = True, doFormat=True, singleLines= False )


####-------------------------------------------------------------------------####
	def filternumbers_1_100(self, filter="", valuesDict=None , typeId=None):
		"""Builds a selection list of the numbers 1 through 99 as [n, n] pairs for use in a config UI menu list.

		Inputs:
		    filter (str): Indigo list filter string (unused)
		    valuesDict (dict or None): current config UI values (unused)
		    typeId (str or None): Indigo config UI type identifier (unused)
		Outputs:
		    list: list of [int, int] pairs for numbers 1 to 99
		"""
		xList = []
	
		for ii in range(1,100):
			xList.append([ii, ii])
		return xList


	####-----------------	 ---------
	def printHelp(self,  valuesDict=None , typeId=""):
		"""Assembles a large multi-line help text describing what the plugin does, installation steps, the iPhone shortcut setup, and the supported voice commands, then logs it to the Indigo log at level 20.

		Inputs:
		    valuesDict (dict or None): config UI values (unused)
		    typeId (str): Indigo config UI type identifier (unused)
		Outputs:
		    None: writes the full help text to the Indigo log
		"""
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
			out += ' siri sometimes does not produce a "1" but "one" two etc \n'
			out += '      the plugin will replace null / zero ... twelve to 0,1,2,3,.. 12 \n'
			out += '        also for german, french, spanish - if you need another language, let me know - we could also do dialects ;) \n'
			out += '\n'
			out += '====  commands ====================================================\n'
			out += '   substitute <device>   with device name     or synonym or  "device id:<devId>:"     or "deviceid:<devId>:" \n'
			out += '   substitute <variable> with variable name   or synonym or  "variable id:<varId>:"   or "variableid:<varId>" \n'
			out += '   substitute <action>   with action synonym  or             "action id:<actionId>:"  or "actionid:<actionId>"  or the exact action group name (lower case)\n'
			out += '   substitute <state>    with state name  \n'
			out += '   substitute <value>    with value to be used \n'
			out += '   upper and lower cases are ignored\n'
			out += '   To make find dev anmes etc easier : \n'
			out += '     commands  and names received will be "normalized:" \n'
			out += '        "_"  and "-" "?" "."  will be replaced by " " \n'
			out += '     indigo device and variable names and state names will be normalized:" \n'
			out += '        "abcDef"  will be replaced by "abc def"  \n'
			out += '        "_"  and "-"  will be replaced by " " \n'
			out += '   then incoming and indigo names etc can be better compared\n'
			out += '   \n'
			out += ' commands: \n'
			out += '   set variable <variable> to value                                      write value to variable, must contain "to"  \n'
			out += '   get variable <variable>                                               get var value and speak it\n'
			out += '   get <device> state <state>                                            get dev/state value and speak it\n'
			out += '                                                                         notice the differnce to get variable \n'
			out += '   (set) speed <device> (to) xx                                          for fans; (0-4 or 100)  one, two are mapped to 1, 2\n'
			out += '   beep <device>  \n'
			out += '   lock <device>  \n'
			out += '   unlock <device>  \n'
			out += '   turn on/off <device>                                              \n'
			out += '   turn  <device> on/off                                             \n'
			out += '   toggle <device>                                                   \n'
			out += '   pulse <device> <secs>  (seconds)                                      on for <secs>  then off, default = 1 secs     \n'
			out += '   dip <device> <secs>  (seconds)                                        off for <secs> then on,  default = 1 secs     \n'
			out += '   (set) heat (temperature) <device> to <degrees> (temperature, degrees) for thermostates to set heat target temp \n'
			out += '   (set) cool (temperature) <device> to <degrees> (temperature, degrees) for thermostatesto seth ac target temp\n'
			out += '   (set) bright(ness level) <device> (to) <value> (percent / %)          will set brightess of dimmer device to <value> 0..100  \n'
			out += '   <action synonym>                                                      will run the Indigo Action Group mapped to that synonym (see Define Action Synonymes)\n'
			out += '   <indigo action group name>                                            plain (straight) action command: speak the name of an Indigo Action Group to run it directly, no synonym needed\n'
			out += '                                                                         must be enabled in config ("enable straight action command"); matches exact name first, then ignoring case/spaces/"/"\n'
			out += '   " and "  or  "&""  or  " then "                                       can be used to concatenate several commands"\n'
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
			out += '   turn office lights on                                             will turn on office lights and the phone will speak "ok" or "turned on" depending on settings \n'
			out += '   turn off deviceid:12345:                                           will turn on indigo device with id 12345 \n'
			out += '   toggle deviceid:12345:                                            will toggle indigo device with id 12345 \n'
			out += '   pulse deviceid:12345: 5 sec                                       will turn on indigo device with id 12345 for 5 secs then off\n'
			out += '   dip office lights                                                 will turn off indigo device  "office lights" for 1 secs then on - 1 is the default\n'
			out += '   open garage                                                       will be execute that action if you have defined "open garage" as a synonym for an action\n'
			out += '   good night                                                        plain action command: runs the Indigo Action Group named exactly "good night", no synonym needed\n'
			out += '   actionid:54321                                                    will execute indigo action with id 54321 if it exists\n'
			out += '   bright <device1> to xx and wait 5 and turn on <device2>           will execute 3 commands  \n'
			out += '   turn on ;SKD;ASJ  on                                              will fail and the iphone will speak "not executed" or "device not found" depending on settings \n'
			out += '\n'
			out += '\n'

			self.indiLOG.log(20,out)
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return


	####-----------------	 ---------
	def printConfig(self,  valuesDict=None , typeId=""):
		"""Assembles a multi-line report of the current plugin configuration (timing, variable/folder names, feedback settings, word mappings, defined action/device/variable synonyms, blocked words, and bad-to-good word mappings) and logs it to the Indigo log at level 20.

		Inputs:
		    valuesDict (dict or None): config UI values (unused)
		    typeId (str): Indigo config UI type identifier (unused)
		Outputs:
		    None: writes the current configuration summary to the Indigo log
		"""
		try:
			out = '\n'
			out += '\n'
			out += 'Plugin config Parameters ===========\n'
			out += f'allow_delta_time        = {self.allow_delta_time}\n'
			out += '                           message must not be older thn current timestamp +  allow_delta_time\n'
			out += '\n'
			out += f'expect_time_tag         = {self.expect_time_tag}\n'
			out += '                           require time stamp value as first work in message\n'
			out += f'var_name                = {self.var_name}\n'
			out += '                           name of the variable the plugin will listen to, will be created if it does not exist\n'
			out += '\n'
			out += f'var_name_feedback       = {self.var_name_feedback}\n'
			out += '                           name of the variable the plugin will write result to be pickup by iphone, will be created if it does not exist\n'
			out += f'folder_name             = {self.folder_name}\n'
			out += '                           folder name of the variables, will be created if it does not exist\n'
			out += '\n'
			out += f'list devices max        = {self.list_devices_max}\n'
			out += '                           list max number of devices when receiving command list devices\n'
			out += '\n'
			out += f'return feedback         = {self.return_feedback}\n'
			out += '                           return what to iphone  "blank" or "ok/not executed" or detailed info\n'
			out += '\n'

			out += f'return strings if successful ============================ if return feedback = detailed\n'
			for xx in self.feedback_ok:
				out += f'                            {xx:15} -> {self.feedback_ok[xx]} \n'

			out += f'command word mapping       ===============================\n'
			for xx in self.translate:
				out += f'                            {xx:15} -> {self.translate[xx]} \n'
				
			out += f'Defined synonymes for actions:       =============================== \n'
			out +=     '     voice phrase         --> action id = indigo name ------------\n'
			for syn in self.synonymes_for_actions:
				devId = int(self.synonymes_for_actions[syn])
				out+= f'     {syn:21s}{devId:13} = {indigo.actionGroups[devId].name}\n'
			out += '\n'
			
			out += f'Defined synonymes for devices:       ===============================\n'
			out +=     '     voice phrase         --> device id = indigo name ------------\n'
			for syn in self.synonymes_for_devices:
				devId = int(self.synonymes_for_devices[syn])
				out+= f'     {syn:21s}{devId:13} = {indigo.devices[devId].name};\n'
			out += '\n'
			
			out += f'Defined synonymes for variables:     ===============================\n'
			out +=     '     voice phrase       --> variable id = indigo name ------------\n'
			for syn in self.synonymes_for_variables:
				devId = int(self.synonymes_for_variables[syn])
				out+= f'     {syn:21s}{devId:13} = {indigo.variables[devId].name}\n '
			out += '\n'
			
			out += f'blocked_words           = {self.blocked_words}\n'
			out += '                           words that are not allowed for devices and actions eg "alarm", when they are present the whole command is ignored\n'
			out += '\n'

			out += 'bad to good words:          bad                good\n'
			for xx in self.map_from_to:
				out += f'                            {xx:15} -> {self.map_from_to[xx]} \n'
			out += '                           bad phrases to be replaced by good phrases \n\n'

			self.indiLOG.log(20,out)
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return


	####-------------------------------------------------------------------------####
	def printStats(self, valuesDict=None, id=None):
		"""Builds a formatted multi-line report of failed and OK voice command statistics (each command with its occurrence count and timestamps) and writes it to the Indigo log at info level.

		Inputs:
		    valuesDict (dict or None): unused config/values dictionary from the UI
		    id (object or None): unused dialog/element identifier
		Outputs:
		    None: logs the formatted stats report
		"""
		try:
			out = '\n'
			out += '\n'
			out += '====================== STATS ==================================\n'
			out += '\n'
			out += '=== FAILED commands                        count             dates ============================================================================================='
			for xx in self.failed_commands:
				nn = len(self.failed_commands[xx])
				out += f'\n{xx.strip():45}{nn:3} times'
				kk = 99
				for yy in range(nn):
					kk += 1
					if kk > 6: 
						out += f'\n{" "*49}'
						kk = 0
					out += f'{self.failed_commands[xx][yy]}; '  
			out += '\n===========================================================\n'
			out += '\n'
			
			out += '\n===========================================================\n'
			out += '=== OK commands                            count             dates ============================================================================================='
			for xx in self.ok_commands:
				nn = len(self.ok_commands[xx])
				out += f'\n{xx.strip():45}{nn:3} times'
				kk = 99
				for yy in range(nn):
					kk += 1
					if kk > 6: 
						out += f'\n{" "*49}'
						kk = 0
					out += f'{self.ok_commands[xx][yy]}; '  
			out += '\n'
			out += '====================== STATS END ==============================\n'
			self.indiLOG.log(20,out)
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return


	####-----------------	 ---------
	def resetStats(self, valuesDict=None, id=None):
		"""Clears the in-memory failed and OK command statistics, persists the now-empty dictionaries to their JSON files, and reports a confirmation message back in valuesDict.

		Inputs:
		    valuesDict (dict): UI values dict that receives the 'MSG' confirmation
		    id (object or None): unused dialog/element identifier
		Outputs:
		    dict: the valuesDict with MSG set to 'stats resetted'
		"""
		self.failed_commands = dict()
		self.ok_commands = dict()
		self.writeJson(self.failed_commands, fName=self.indigoPreferencesPluginDir + "failed_commands.json", verbose=False)
		self.writeJson(self.ok_commands, fName=self.indigoPreferencesPluginDir + "ok_commands.json", verbose=False)
		valuesDict ["MSG"] = "stats resetted"
		return valuesDict


	####-----------------	 ---------
	def setDebugFromPrefs(self, theDict: dict, writeToLog=True):
		"""Rebuilds the list of active debug areas from boolean 'debug<area>' flags in the given preferences dict, optionally logging the resulting enabled areas.

		Inputs:
		    theDict (dict): preferences dictionary holding debug area flags
		    writeToLog (bool): whether to log the resulting debug areas
		Outputs:
		    None: updates self.debugAreas and optionally logs
		"""
		self.debugAreas = []
		try:
			for d in _debugAreas:
				if theDict.get("debug"+d, False): self.debugAreas.append(d)
			if writeToLog: self.indiLOG.log(20, "debug areas: {} ".format(self.debugAreas))
		except	Exception as e:
				if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)


	####-----------------	 ---------
	def completePath(self, inPath:str):
		"""Normalizes a directory path string by returning empty string for blank input and otherwise ensuring it ends with a trailing slash.

		Inputs:
		    inPath (str): path string to normalize
		Outputs:
		    str: the path with a trailing slash, or empty string
		"""
		if len(inPath) == 0: return ""
		if inPath == " ":	 return ""
		if inPath[-1] !="/": inPath +="/"
		return inPath


	####-------------------------------------------------------------------------####
	def readJson(self, fName:str, defReturn={}):
		"""Reads and parses a JSON file from disk, returning the decoded object; if the file does not exist or an error occurs it returns the provided default.

		Inputs:
		    fName (str): path of the JSON file to read
		    defReturn (dict): default value returned when file missing or on error
		Outputs:
		    dict: the parsed JSON data or the default value
		"""
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
		"""Serializes data to JSON (or a simple key:value line format), optionally writing it to the given file, and returns the serialized string.

		Inputs:
		    data (dict): data to serialize
		    fName (str): file path to write to, or empty to skip writing
		    sort (bool): whether to sort keys in the JSON output
		    doFormat (bool): whether to pretty-format the output
		    singleLines (bool): use one line per key instead of JSON when formatting
		    verbose (bool): whether to log the serialized output
		Outputs:
		    str: the serialized output, or empty string for empty/None data or on error
		"""
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
		"""Runs a shell command via subprocess and returns its stdout and stderr decoded as UTF-8 strings.

		Inputs:
		    cmd (str): shell command to execute
		Outputs:
		    tuple: (stdout, stderr) decoded strings, or None on error
		"""
		try:
			ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			return ret.decode('utf-8'), err.decode('utf-8')

		except Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)


	####-------------------------------------------------------------------------####
	def openEncoding(self, fName: str , readOrWrite: str):

		"""Opens a file handle in the requested mode, using UTF-8 encoding for text modes (codecs.open on Python 2) and plain binary open when the mode contains 'b'.

		Inputs:
		    fName (str): path of the file to open
		    readOrWrite (str): file open mode such as 'r', 'w', or 'rb'
		Outputs:
		    object: the open file handle, or None on error
		"""
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

		"""Validates and applies the plugin preferences when the prefs dialog is closed, copying timing and variable-name settings into instance attributes and flagging variables to be re-initialized.

		Inputs:
		    valuesDict (dict): preferences values from the config dialog
		Outputs:
		    tuple: (True, valuesDict) on success or (False, errorDict, valuesDict) on error
		"""
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

		"""Performs one-time initialization before the main loop: records current minute/hour, writes the data version file, initializes variables, and subscribes to Indigo variable changes.

		Inputs:
		    None.
		Outputs:
		    bool: True after initialization completes
		"""
		nowDT = datetime.datetime.now()
		self.lastMinute		= nowDT.minute
		self.lastHour		= nowDT.hour
		self.writeJson({"version":_dataVersion}, fName=self.indigoPreferencesPluginDir + "dataVersion")
		self.initVariables()
		indigo.variables.subscribeToChanges()
		return True


	####-----------------   main loop          ---------
	def runConcurrentThread(self):

		"""The plugin's main background thread: runs startup init then loops once per second re-initializing variables when flagged, exits when quitNOW is set, saves prefs, and restarts the plugin if a quit reason was given.

		Inputs:
		    None.
		Outputs:
		    None: runs the main loop, logs, saves prefs, and may restart the plugin
		"""
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

	####-------------------------------------------------------------------------####
	def variableUpdated(self, orig_var: dict, new_var: dict ):
		"""Callback fired when a subscribed Indigo variable changes; for the monitored command variable it resets feedback, dispatches the new value to the action handler, and updates the feedback variable with the result or a 'not finished' marker.

		Inputs:
		    orig_var (indigo.Variable): the variable's prior state
		    new_var (indigo.Variable): the variable's updated state with new value
		Outputs:
		    None: updates the feedback variable and triggers the command action
		"""
		if self.var_name != orig_var.name: return 
		self.feedback_value = " "
		indigo.variable.updateValue(self.var_name_feedback, value=" ")
		self.variableUpdated_action(new_var.value)

		
		if self.feedback_value != " ":	indigo.variable.updateValue(self.var_name_feedback, value=self.feedback_value)
		else			: 				indigo.variable.updateValue(self.var_name_feedback, value="not finshed")
		
		return  


	####-------------------------------------------------------------------------####
	def variableUpdated_action(self, new_var:str ):
		"""Indigo variable-change callback that treats the new variable value as an incoming voice command: it strips time tags, normalizes the text, handles built-in commands (list devices, test, debug on/off, help, silence), then splits compound commands and dispatches each sub-command to handle_wait/execute_actions_for_command, updating the feedback variable.

		Inputs:
		    new_var (str): raw command text from the watched Indigo variable
		Outputs:
		    None: processes the command, logs, runs actions and updates the feedback variable/stats
		"""
		try:
			if self.decideMyLog("ReceivdeData"): self.indiLOG.log(20, f'var changed  "{new_var}"')
				
			self.raw = new_var
	
			if self.decideMyLog("ReceivdeData"): self.indiLOG.log(20, f"Command received raw: '{self.raw}'")
	
			if not self.raw or not self.raw.strip():
				return
	

			ok, raw_stripped = self.check_if_time_tag_ok(self.raw.strip())
			if not ok: 
				return 
	
			if self.decideMyLog("ReceiveData"): self.indiLOG.log(20, f"Command received raw, tags removed: '{raw_stripped}'")
	
			# replace _- A -> a string, remove double spaces etc 
			cmd =  self.normalize_incoming(raw_stripped)
			
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
					nn = 0
					for sub in sub_cmds:
						nn +=1
						if not self.handle_wait(sub):
							if not self.execute_actions_for_command(sub):
								if self.feedback_value == " ":
									self.stats_good(False, "no match found")
						if nn == 1:
							indigo.variable.updateValue(self.var_name_feedback, value=self.feedback_value)
			else:
				if not self.handle_wait(cmd):
					if not self.execute_actions_for_command(cmd):
						if self.feedback_value == " ":
							self.stats_good(False, "no match found")

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return 


	####-------------------------------------------------------------------------####
	def execute_actions_for_command(self, cmd_in: str):
	
		# 1.1 check if this is something with explicit  xxxid:
		"""Resolves and executes the action for a normalized command: handles explicit 'device id:'/'variable id:' patterns, 'action id:' direct action-group execution, synonym-mapped action groups, and otherwise falls back to try_pattern_commands for device/variable commands.

		Inputs:
		    cmd_in (str): normalized command string to match and execute
		Outputs:
		    bool: True if a matching action/pattern was executed, False if no match
		"""
		if  cmd_in.find("device id:") > -1 or cmd_in.find("variable id:") > -1:
			if self.try_pattern_commands(cmd_in): return True
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"No match for '{cmd_in}' in ACTIONs or patterns")
			return False

		# actionid:1234:
		if  cmd_in.find("action id:") > -1:
			xx = cmd_in.strip(":").strip(" ").split("action id:")
				
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
				return True
			self.stats_good(False,"acton not present")
			return True
	
		# 1.2 check if this is an action known under synonym:
		synonymId = int(self.synonymes_for_actions.get(cmd_in, 0))

		if synonymId != 0:
			if self.decideMyLog("logic"): self.indiLOG.log(20, f"execute_actions_for_command '{cmd_in}' - action Id:{synonymId} = {indigo.actionGroups[synonymId].name}")
			indigo.actionGroup.execute(synonymId)
			self.stats_good(True, "action executed")
			return True
			
				
		# second check if this is an dev var .. command:
		if self.try_pattern_commands(cmd_in): return True

		# try if this is a plain (straight) action command: exact action-group name, when enabled 
		if self.try_plainactioncommand_text(cmd_in): return True
			

		if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"No match for '{cmd_in}' in ACTIONs or patterns")
		return False


	####-------------------------------------------------------------------------####
	def try_plainactioncommand_text(self, cmd_in: str) -> bool:
		"""Plain ("straight") action command: when enabled via the 'plainactionCommand' plugin preference, run an Indigo Action Group whose name matches the spoken command - first an exact (100%) name match, then a normalized match that ignores case, spaces and "/". No action synonym needs to be defined.

		Inputs:
		    cmd_in (str): normalized command string, expected to be (close to) the literal name of an Indigo Action Group
		Outputs:
		    bool: True if the feature is enabled and a matching action group was found and executed; False otherwise (including when the feature is disabled)
		"""
		# opt-in via plugin config checkbox "enable straight action command"
		if not self.pluginPrefs.get("plainactionCommand", False): return False

		# 100% exact-name match?
		if cmd_in in indigo.actionGroups:
			indigo.actionGroup.execute(cmd_in)
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_ action command: {cmd_in}")
			self.stats_good(True, self.feedback_ok["action"])
			return True

		# if not, retry ignoring case, spaces and "/" characters
		cmdIn = cmd_in.replace(" ", "").replace("/", "")
		for cmd in indigo.actionGroups:
			if cmd.lower().replace(" ", "").replace("/", "") == cmdIn:
				indigo.actionGroup.execute(cmd)
				if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_ action command: {cmd_in}")
				self.stats_good(True, self.feedback_ok["action"])
				return True
		return False


	####-------------------------------------------------------------------------####
	def try_pattern_commands(self, cmd_in: str) -> bool:
		"""Parses device-id/variable-id patterns from the command (filling self.device or self.variable with [prefix, indigo object, value]) and then tries each device/variable command handler in turn (get value, set variable, speed, beep, pulse, dip, unlock, lock, turn on/off, toggle, set heat/cool, set level).

		Inputs:
		    cmd_in (str): command string possibly containing device/variable id patterns
		Outputs:
		    bool: True if one of the handlers matched/handled the command, False otherwise
		"""
		try:
			# replace white spaces with one blank and strip blanks
			cmd = re.sub(r"\s+", " ", cmd_in.strip()).strip()
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands {cmd} ")

			self.device = []
			self.variable = []
			if cmd_in.find("device id:") > -1:
				if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands received devid ")
				aa = cmd_in.split("device id:")  
				#
				# == turn on, devid: 
				# == turn, devid:, on /off
				# == turn off, devid
				# == bright, devid: (to) value
				# == bright, devid (to) value
				# == get, devid state statename
				# == get, devid: state statename
				
				if len(aa) == 2:
					if ":" in aa[1]:
						yy = aa[1].split(":")
						devid = int(yy[0])
						value = yy[1]
						if devid not in indigo.devices:
							self.stats_good(False,"device i d not found")
							if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands 1 dev id not found")
							return True
						self.device = [aa[0], indigo.devices[devid], value]
						if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands device: {self.device} ")
					else:  # turn on device id: id#  value   second : is missing
						pos = aa[1].find(" ")
						if pos > -1:
							devid = int(aa[1][:pos])
							if devid not in indigo.devices:
								self.stats_good(False,"device i d not found")
								if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands 2 dev id not found")
								return True
							value = aa[1][pos+1:]
							self.device = [aa[0], indigo.devices[devid], value]
							if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands device: {self.device} ")
						else:
							devid = int(aa[1])
							value = ""
							if devid not in indigo.devices:
								self.stats_good(False,"device i d not found")
								if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands 3 dev id not found")
								return True
							self.device = [aa[0], indigo.devices[devid], ""]
							if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands device: {self.device} ")
				else:
					self.stats_good(False,"id missing")
					return True
	
			elif cmd_in.find("variable id:") > -1:
				# set variableid:13345: newvalue
				# set variableid:13345 newvalue
				# get variableid:13345:
				# get variableid:13345
				if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands received varid ")
				xx = cmd_in.split("variable id:")
				if len(xx) == 2:
					if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands split var id: {xx}")
					if ":" in xx[1]:
						yy = xx[1].split(":")
						valid = int(yy[0])
						value = yy[1]
						if valid not in indigo.variables:
							self.stats_good(False,"variable i d not found")
							if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands 1 variable id not found")
							return True
						self.variable = [xx[0], indigo.variables[valid], value]
						if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands variable: {self.variable} ")
					else:
						pos = xx[1].find(" ")
						if pos > -1:
							valid = int(xx[1][:pos])
							if valid not in indigo.variables:
								self.stats_good(False,"variable i d not found")
								if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands 1 variable id not found")
								return True
							value = xx[1][pos+1:]
							self.variable = [xx[0], indigo.variales[valid], value]
							if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands variable: {self.variable} ")
						else:
							valid = int(xx[1])
							if valid not in indigo.variables:
								self.stats_good(False,"variable i d not found")
								if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands 1 variable id not found")
								return True
							value = ""
							self.variable = [xx[0], indigo.variales[valid], value]
							if self.decideMyLog("Logic"): self.indiLOG.log(20, f"try_pattern_commands variable: {self.variable} ")
				else:
					self.stats_good(False,"id missing")
					return True

			###get variable or device / state value  ##
			if self.handle_get_value(cmd): return  True

			### variables  first must have "set variable name to xx "
			if self.handle_set_variable(cmd): return  True

			### devices ##
			if self.handle_set_speed(cmd): return True

			if self.handle_beep(cmd): return True

			if self.handle_pulse(cmd): return True

			if self.handle_dip(cmd): return True

			if self.handle_unlock(cmd): return True

			if self.handle_lock(cmd): return True
			
			if self.handle_turn_on_off(cmd): return True
	
			if self.handle_toggle(cmd): return  True

			if self.handle_set_heat(cmd): return  True

			if self.handle_set_cool(cmd): return  True

			if self.handle_set_level(cmd): return  True

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return False


	# ==========================
	#  META COMMANDS
	# ==========================
	
	####-------------------------------------------------------------------------####
	def log_available_commands(self):
		"""Logs all available ACTION voice commands by printing each synonym key (sorted) that maps voice phrases to Indigo action groups.

		Inputs:
		    None.
		Outputs:
		    None: writes the list of action synonyms to the log
		"""
		self.indiLOG.log(20,"Available ACTION commands: that are mapped from voice to actual indigo action groups")
		for cmd in sorted( self.synonymes_for_actions.keys()):
			self.indiLOG.log(20, f"  {cmd}")
	
	####-------------------------------------------------------------------------####
	def log_devices(self):
		"""Logs the list of Indigo devices showing each device name alongside its normalized match form, truncating once self.list_devices_max devices have been printed.

		Inputs:
		    None.
		Outputs:
		    None: writes the device name to normalized mapping to the log
		"""
		self.indiLOG.log(20,"Device list (name → normalized) [truncated if large]:")
		count = 0
		for dev in indigo.devices:
			if count >=  self.list_devices_max:
				self.indiLOG.log(20, f"... truncated at {self.list_devices_max} devices ...")
				break
			self.indiLOG.log(20, f"   {dev.name:55} → {self.normalize_indigo_for_match(dev.name)}")
			count += 1

	# ==========================
	#  device/ var EXECUTION
	# ==========================


	# handle updates
	####-------------------------------------------------------------------------####
	def handle_wait(self, cmd_in: str) -> bool:
		"""If the command contains the 'wait' keyword, parses a numeric duration after it and sleeps for that many seconds before returning, used to insert delays between compound sub-commands.

		Inputs:
		    cmd_in (str): command string possibly containing a wait/delay instruction
		Outputs:
		    bool: True if the command was a wait command (handled), False if it was not a wait command
		"""
		if cmd_in.find(self.translate["wait"]) > -1:
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_wait received command: '{cmd_in}'")
			test = cmd_in.lower().split(self.translate["wait"])[1].strip()
			pos, level, cmd = self.check_if_float(test)
			if pos == -1:
				self.stats_good(False, "wait no number")
				if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_wait '{cmd_in}'  no number")
				return True
			self.sleep(level)
			self.stats_good(True, self.feedback_ok["wait"])
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_wait '{cmd_in}'wait for  {level} secs")
			return True
		return False


	####-------------------------------------------------------------------------####
	def handle_set_speed(self, cmd_in: str) -> bool:
		
		#  cmd:  (set) speed device (to) xx
		"""Handles a 'set speed ... to N' command: extracts the speed level and target device (from a pre-parsed device id or by name matching), verifies the device has a speedLevel property, and sets its speed index via indigo.speedcontrol.setSpeedIndex.

		Inputs:
		    cmd_in (str): command string containing the speed keyword and value
		Outputs:
		    bool: True if the command was a speed command (handled or attempted), False if not a speed command
		"""
		pos = cmd_in.find(self.translate["speed"]+" ")
		if pos < 0: return False
		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_speed '{cmd_in}' speed at pos {pos}")

		if self.device != []:
			cmd_in = self.device[2]
			dev = self.device[1]
			cmd = self.strip_words(cmd_in,["%","percent","level"])
			cmd = self.remove_lastword(cmd, "%", 1)
			cmd = self.remove_lastword(cmd, "per", 1)
			cmd = self.remove_lastword(cmd, self.translate["level"], 2)
			pos, level, cmd = self.check_if_int(cmd)
			if pos == -1:
				self.stats_good(False, "speed no number")
				if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_wait '{cmd_in}' no number")
				return True
			cmd = self.remove_lastword(cmd, self.translate["to"], 1)
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_speed '{dev.name}' speed {level}")

		else:
			#
			#0123456789012345678901234567890:			
			#heat office 20 
			#heat deviceid:12345678: to 20 
			cmd = cmd_in.split(self.translate["speed"]+" ")[1]
			cmd = self.strip_words(cmd,["%","percent","level"])
			cmd = self.remove_lastword(cmd, "%", 1)
			cmd = self.remove_lastword(cmd, "per", 1)
			cmd = self.remove_lastword(cmd, self.translate["level"], 2)
			pos, level, theName = self.check_if_int(cmd, first=1)
			if pos == -1:
				self.stats_good(False, "speed no number")
				if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_speed '{cmd_in}' no number")
				return True
			cmd = self.remove_lastword(cmd, self.translate["to"], 1)
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_speed dev '{cmd}'")

			dev = self.check_if_match_devices(theName)
			if not dev:
				if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"handle_set_speed No device found matching '{theName}'")
				self.stats_good(False, "device not found")
				return True
				
		if  not self.check_if_property( dev, "speedLevel", "not available"): return True
		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_speed found '{theName}' {level}")
				
		try:
			indigo.speedcontrol.setSpeedIndex(dev.id, value=level)
			self.stats_good(True, self.feedback_ok["speed"])
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_speed '{dev.name}' speed {level}")
			return True
		except:
			self.indiLOG.log(20, f"handle_set_speed not executed")
			self.stats_good(False,"not executed")
		return True


	####-------------------------------------------------------------------------####
	def handle_set_level(self, cmd_in: str) -> bool:
		
		# allow:
		#  set brightness level device to 66 %
		#  set brightness level device to 66 percent
		#  brightness set level device to 66 percent
		#      brightness level device to 66 %
		#      bright device to 66 %
		#      bright device 66 %
		#      bright device 66 
		#   ...

		"""Handles a 'set brightness/level ... to N %' command: parses the level and target device, and either sets dimmer brightness for dimmable devices, or for relay devices turns the device off when level is 0 and on otherwise.

		Inputs:
		    cmd_in (str): command string containing the brightness/level keyword and value
		Outputs:
		    bool: True if the command was a brightness command (handled or attempted), False if not a brightness command
		"""
		pos = cmd_in.find(self.translate["bright"])
		if pos < 0: return False

		if self.device != []:
			cmd = self.strip_words(self.device[2],["%","percent"])
			cmd = self.remove_lastword(cmd, "%", 1)
			cmd = self.remove_lastword(cmd, "per", 1)
			cmd = self.remove_lastword(cmd, self.translate["level"], 2)
			cmd = self.remove_lastword(cmd, self.translate["to"], 2)
			pos, level, cmd = self.check_if_int(cmd)
			if pos == -1:
				self.stats_good(False, "bright no number")
				if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_wait '{cmd_in}' level: {level} secs")
				return True
			dev = self.device[1]
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_level-d '{dev.name}' to {level}")

		else:	
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_level-1'{cmd_in}';  bright at pos {pos}")
			# remove (set)  bright(ness) (level) (to)  
			cmd = self.remove_firstword(cmd_in, self.translate["set"] )
			cmd = self.remove_firstword(cmd, self.translate["bright"] )
			cmd = self.remove_firstword(cmd, self.translate["set"] )
			cmd = self.remove_firstword(cmd, self.translate["to"] )
			cmd = self.remove_firstword(cmd, self.translate["level"] )
				
			# now "device name (to) number (%) (percent)",  remove to % ..
			cmd = self.strip_words(cmd,["%","percent"])
			cmd = self.remove_lastword(cmd, "%", 1)
			cmd = self.remove_lastword(cmd, "per", 1)
			cmd = self.remove_lastword(cmd, self.translate["to"], 2)
			# should have dev name number 
			pos, level, theName = self.check_if_int(cmd, first=1)
			if pos == -1:
				self.stats_good(False, "brightness no number")
				if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_level '{cmd_in}' level:{level} no number")
				return True
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_level-2: {cmd}")
	
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_level1  dev {theName}, level:{level}%")
			dev = self.check_if_match_devices(theName)
			if not dev:
				if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"handle_set_level No device found matching '{theName}'")
				self.stats_good(False, "device not found")
				return True

		if  not self.check_if_property( dev, "brightness", " not available"): return True
		if self.device_is_dimmable(dev):
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"Setting dev '{dev.name}' to {level}%")
			try:
				indigo.dimmer.setBrightness(dev.id, value=level)
				self.stats_good(True, self.feedback_ok["bright"])
				return True
			except:
				self.indiLOG.log(20, f"handle_set_level not executed")
				self.stats_good(False, "not executed")
			return True

		# relay fallback: >0 => ON, 0 => OFF
		if level == 0:
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"Setting dev '{dev.name}' to 0% (relay -> OFF)")
			try:
				indigo.device.turnOff(dev.id)
				self.stats_good(True, self.feedback_ok["bright"])
			except:
				self.indiLOG.log(20, f"handle_set_level not executed")
				self.stats_good(False, "not executed")
		else:
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"Setting dev '{dev.name}' to {level}% (relay -> ON)")
			try:
				indigo.device.turnOn(dev.id)
				self.stats_good(True, self.feedback_ok["bright"])
			except:
				self.indiLOG.log(20, f"handle_set_level not executed")
				self.stats_good(False, "not executed")
		return True


	####-------------------------------------------------------------------------####
	def handle_unlock(self, cmd_in: str) -> bool:

		"""Handles an 'unlock <device>' command: resolves the target device (from pre-parsed device id or by name), checks it has the IsLockSubType plugin property, and calls indigo.device.unlock on it.

		Usage note (original):
		    	how to use this in a plugin:
		    	def actionControlDevice(self, action, dev):
		    		if action.deviceAction == indigo.kDeviceAction.Lock:
		    		   do your thing
		    	and in device definitions
		     		props["IsLockSubType"] = True

		Inputs:
		    cmd_in (str): command string containing the unlock keyword and device
		Outputs:
		    bool: True if the command was an unlock command (handled or attempted), False if not an unlock command
		"""
	
		pos = cmd_in.find(self.translate["unlock"]+" ")
		if pos < 0: return False

		if self.device != []:
			dev = self.device[1]
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_unlock dev '{dev.name}'")

		else:
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_unlock '{cmd_in}'  unlock at pos {pos}")
			theName = cmd_in.split(self.translate["unlock"]+" ")[1]
			dev = self.check_if_match_devices(theName)
			if not dev:
				if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"handle_unlock No device found matching '{theName}'")
				self.stats_good(False, "device not found")
				return True

		if  not self.check_if_property( dev.pluginProps, "IsLockSubType"," not available"): return True
		try:
			indigo.device.unlock(dev.id)
			self.stats_good(True, self.feedback_ok["unlock"])
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"unlock dev '{dev.name}' {result}")
		except:
			self.indiLOG.log(20, f"handle_unlock not executed")
			self.stats_good(False, "not executed")
		return True


	####-------------------------------------------------------------------------####
	def handle_lock(self, cmd_in: str) -> bool:
	
		"""Handles a 'lock <device>' command: resolves the target device (from pre-parsed device id or by name), checks it has the IsLockSubType plugin property, and calls indigo.device.lock on it.

		Inputs:
		    cmd_in (str): command string containing the lock keyword and device
		Outputs:
		    bool: True if the command was a lock command (handled or attempted), False if not a lock command
		"""
		pos = cmd_in.find(self.translate["lock"]+" ")
		if pos < 0: return False

		if self.device != []:
			dev = self.device[1]
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_lock '{dev.name}'")

		else:
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f'handle_lock "{cmd_in}""  "lock"  found @ {pos}')
			theName = cmd_in.split(self.translate["lock"]+" ")[1]
			dev = self.check_if_match_devices(theName)
			if not dev:
				if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"handle_lock No device found matching '{theName}'")
				self.stats_good(False," device not found")
				return True

		if  not self.check_if_property( dev.pluginProps, "IsLockSubType", " not available"): return True
		try:
			indigo.device.lock(dev.id)
			self.stats_good(True, self.feedback_ok["lock"])
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"lock dev '{dev.name}'")
		except:
			self.indiLOG.log(20, f"handle_lock not executed")
			self.stats_good(False, "not executed")
		return True



	####-------------------------------------------------------------------------####
	def handle_beep(self, cmd_in: str) -> bool:


		"""Handles a 'beep <device>' command: resolves the target device (from pre-parsed device id or by name) and triggers the device's beep via indigo.device.beep.

		Usage note (original):
		    how to use this in a plugin:
		    def actionControlUniversal(self, action, dev):
		    	if action.deviceAction == indigo.kUniversalAction.Beep:
		    		do your thing
		    		has no prop defined per default, so no way to check is this action is available

		Inputs:
		    cmd_in (str): command string containing the beep keyword and device
		Outputs:
		    bool: True if the command was a beep command (handled or attempted), False if not a beep command
		"""
		pos = cmd_in.find(self.translate["beep"]+" ")
		if pos < 0: return False

		if self.device != []:
			dev = self.device[1]

		else:
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_beep '{cmd_in}' at pos {pos}")
			theName = cmd_in.split(self.translate["beep"]+" ")[1]
	
			dev = self.check_if_match_devices(theName)
			if not dev:
				if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"Nhandle_beep o device found matching '{theName}'")
				self.stats_good(False, "device not found")
				return True

		#  not supported by indigo 
		#if  not self.check_if_property( dev, "hasbeep", "beep not available"): return True
		
		
		if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_beep beep dev '{dev.name}'")
		try:
			indigo.device.beep(dev.id)
			self.stats_good(True, self.feedback_ok["beep"])
		except:
			self.indiLOG.log(20, f"handle_beep not executed")
			self.stats_good(False, "not executed")
		return True


	####-------------------------------------------------------------------------####
	def handle_pulse(self, cmd_in: str) -> bool:
		# pulse <device> 5 (seconds)
		"""Handles a 'pulse <device> N seconds' command: resolves the target device and pulse duration (defaulting to 1 second), checks the device has an onState, then turns it on, sleeps for the duration, and turns it off.

		Inputs:
		    cmd_in (str): command string containing the pulse keyword, device and optional duration
		Outputs:
		    bool: True if the command was a pulse command (handled or attempted), False if not a pulse command
		"""
		pos = cmd_in.find(self.translate["pulse"])
		if pos < 0: return False
		if pos >10: return False

		if self.device != []:
			dev = self.device[1]
			cmd = self.device[2]
			cmd = self.strip_words(cmd,["sec","seconds","sekunden","sek","set"])
			cmd = self.remove_lastword(cmd, "sec", 2)
			cmd = self.remove_lastword(cmd, "sek", 2)
			cmd = self.remove_lastword(cmd, self.translate["set"], 3)
			cmd = self.remove_lastword(cmd, self.translate["to"], 2)
			pos, level, theName = self.check_if_float(cmd)
			if pos == -1: 
				level = 1.
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_pulse '{dev.name}', pulse:{level} secs")

		else:
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_pulse '{cmd_in}'  pulse at pos {pos}")
			cmd = cmd_in[pos+len(self.translate["pulse"]):].strip() # removed "pulse "
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_pulse-2 '{cmd}'")
			cmd = self.strip_words(cmd,["sec","seconds","sekunden","sek","set"])
			cmd = self.remove_lastword(cmd, "sec", 2)
			cmd = self.remove_lastword(cmd, "sek", 2)
			cmd = self.remove_lastword(cmd, self.translate["set"], 3)
			cmd = self.remove_lastword(cmd, self.translate["to"], 2)
			pos, level, theName = self.check_if_float(cmd, first=1)
			if pos == -1: 
				level = 1.
			
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_pulse dev {theName}, secs {level}, cmd:{cmd}")
	
			dev = self.check_if_match_devices(theName)
			if not dev:
				if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"handle_pulse No device found matching '{theName}'")
				self.stats_good(False, "device not found")
				return True

		if  not self.check_if_property( dev, "onState", "on state not available"): return True
		if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_pulse turn on  dev '{dev.name}' for secs  {level}")


		try:	
			indigo.device.turnOn(dev.id)
			self.stats_good(True, self.feedback_ok["pulse"])
			self.sleep(level)
			indigo.device.turnOff(dev.id)
		except:
			self.indiLOG.log(20, f"handle_pulse not executed")
			self.stats_good(False, "not executed")
		return True


	####-------------------------------------------------------------------------####
	def handle_dip(self, cmd_in: str) -> bool:
		# dip <device> 5 (seconds)
		"""Handles a 'dip' voice command by parsing an optional duration (in seconds) and a target device name, then briefly turns the device off, waits, and turns it back on (a momentary pulse). Defaults the pulse duration to 1 second if no number is given.

		Inputs:
		    cmd_in (str): the incoming normalized voice command text
		Outputs:
		    bool: False if the 'dip' keyword is absent/misplaced, otherwise True after attempting the pulse and recording stats
		"""
		pos = cmd_in.find(self.translate["dip"])
		if pos < 0: return False
		if pos >10: return False

		if self.device != []:
			dev = self.device[1]
			cmd = self.device[2]
			cmd = self.strip_words(cmd,["sec","seconds","sekunden","sek","set"])
			cmd = self.remove_lastword(cmd, "sec", 2)
			cmd = self.remove_lastword(cmd, "sek", 2)
			cmd = self.remove_lastword(cmd, self.translate["set"], 3)
			cmd = self.remove_lastword(cmd, self.translate["to"], 2)
			pos, level, theName = self.check_if_float(cmd)
			if pos == -1: 
				level = 1.
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_dip '{dev.name}', pulse:{level} secs")

		else:
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_dip '{cmd_in}'  pulse at pos {pos}")
			cmd = cmd_in[pos+len(self.translate["dip"]):].strip() # removed "pulse "
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_pulse-2 '{cmd}'")
			cmd = self.strip_words(cmd,["sec","seconds","sekunden","sek","set"])
			cmd = self.remove_lastword(cmd, "sec", 2)
			cmd = self.remove_lastword(cmd, "sek", 2)
			cmd = self.remove_lastword(cmd, self.translate["set"], 3)
			cmd = self.remove_lastword(cmd, self.translate["to"], 2)
			pos, level, theName = self.check_if_float(cmd, first=1)
			if pos == -1: 
				level = 1.
			
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_dip dev {theName}, secs {level}, cmd:{cmd}")
	
			dev = self.check_if_match_devices(theName)
			if not dev:
				if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"handle_dip No device found matching '{theName}'")
				self.stats_good(False, "device not found")
				return True

		if  not self.check_if_property( dev, "onState", "on state not available"): return True
		if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_dip turn off  dev '{dev.name}' for secs  {level}")


		try:	
			indigo.device.turnOff(dev.id)
			self.stats_good(True, self.feedback_ok["dip"])
			self.sleep(level)
			indigo.device.turnOn(dev.id)
		except:
			self.indiLOG.log(20, f"handle_dip not executed")
			self.stats_good(False, "not executed")
		return True


	####-------------------------------------------------------------------------####
	def handle_turn_on_off(self, cmd_in: str) -> bool:
		# turn on / off<device>
		"""Handles a 'turn on/off <device>' voice command, parsing the requested on/off state and the device name, then turns the device on or off (using brightness 100/0 for dimmable devices, or turnOn/turnOff otherwise).

		Inputs:
		    cmd_in (str): the incoming normalized voice command text
		Outputs:
		    bool: False if the command does not start with the 'turn' keyword, otherwise True after attempting the action and recording stats
		"""
		pos = cmd_in.find(self.translate["turn"])
		if pos != 0: return False

		if self.device != []:
			dev = self.device[1]
			if len(self.device[2]) > 0:
				cmd = self.device[2].strip()
				if cmd.find(self.translate["on"]) > -1: state = "on"
				elif cmd.find(self.translate["off"]) > -1: state = "off"
				else: state = "on"
			else:
				cmd = self.device[0].strip().split(" ")
				if len(cmd) == 2:
					state = cmd[1]
				else:
					state = "on"
					
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_turn_on_off w devId:: '{dev.name}', state:{state}")

		else:
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_turn_on_off w  cmd: '{cmd_in}'  turn at pos {pos}")
			cmd = " "+cmd_in[pos+len(self.translate["turn"]):]+" " # removed "turn "
			pos_on  = cmd.find(" "+self.translate["on"]+" ")
			pos_off = cmd.find(" "+self.translate["off"]+" ")
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_turn_on_off w  cmd: '{cmd}'  turn at pos {pos_on}  {pos_off}")
			if pos_on < 0 and pos_off < 0: 
				if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f'string "on / off"  not found in {cmd_in}')
				self.stats_good(False, "on / off  not found")
				return True

			cmd = cmd.strip().split(" ") #
			if pos_on >= 0:
				if pos_on < 5: # in first pos
					state = cmd[0].strip()
					theName = " ".join(cmd[1:]).strip() # rest is dev name
				else: # "on" is at the end
					state = cmd[-1].strip()
					theName = " ".join(cmd[:-1]).strip() #beginning is
			if pos_off >= 0:
				if pos_off < 5: # in first pos
					state = cmd[0].strip()
					theName = " ".join(cmd[1:]).strip() # rest is dev name
				else: # "off" is at the end
					state = cmd[-1].strip()
					theName = " ".join(cmd[:-1]).strip() #beginning is
			
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_turn_on_off devname: {theName}, turn {state}")
	
			dev = self.check_if_match_devices(theName)
			if not dev:
				if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"No device found matching '{theName}'")
				self.stats_good(False, "device not found")
				return True
				
		if  not self.check_if_property( dev, "onState", "on state not available"): return True
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
			
		except:
			self.indiLOG.log(20, f"handle_turn_on_off not executed")
			self.stats_good(False, "not executed")
		return True


	####-------------------------------------------------------------------------####
	def handle_toggle(self, cmd_in: str) -> bool:
	
		"""Handles a 'toggle <device>' voice command, resolving the target device and calling indigo.device.toggle to flip its on/off state.

		Inputs:
		    cmd_in (str): the incoming normalized voice command text
		Outputs:
		    bool: False if the 'toggle' keyword is absent, otherwise True after attempting the toggle and recording stats
		"""
		pos = cmd_in.find(self.translate["toggle"]+" ")
		if pos < 0: return False
	
		if self.device != []:
			dev = self.device[1]
		else:
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_toggle {cmd_in}")
			theName = cmd_in[pos+len(self.translate["toggle"]):].strip() # removed "turn "
			dev = self.check_if_match_devices(theName)
			if not dev:
				if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"handle_toggle No device found matching '{theName}'")
				self.stats_good(False, "device not found")
				return True

		if  not self.check_if_property( dev, "onState", " on state not available"): return True
		if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_toggle dev '{dev.name}'")

		try:
			indigo.device.toggle(dev.id)
			self.stats_good(True, self.feedback_ok["toggle"])
		except:
			self.indiLOG.log(20, f"handle_toggle not executed")
			self.stats_good(False, "not executed")
		return True



	####-------------------------------------------------------------------------####
	def handle_set_heat(self, cmd_in: str) -> bool:
		# (set) heat <device> (to) xx 
		"""Handles a 'set heat <device> to <temp>' voice command, stripping temperature unit words, parsing the numeric setpoint and device name, then setting the thermostat's heat setpoint.

		Inputs:
		    cmd_in (str): the incoming normalized voice command text
		Outputs:
		    bool: False if the 'heat' keyword is absent, otherwise True after attempting to set the heat setpoint and recording stats
		"""
		pos = cmd_in.find(self.translate["heat"]+" ")
		if pos < 0: return False


		if self.device != []:
			dev = self.device[1]
			cmd = self.device[2]
			cmd = self.strip_words(cmd, ["celsius","fahrenheit","degrees","degree","deg","grad","temperature","temperatur"])
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_heatl-1 {cmd}")
			cmd = self.remove_word(cmd, self.translate["of"])
			cmd = self.remove_lastword(cmd, "cel", 1)
			cmd = self.remove_lastword(cmd, "fahr", 1)
			cmd = self.remove_lastword(cmd, "deg", 2)
			cmd = self.remove_lastword(cmd, "temp", 2)
			cmd = self.remove_lastword(cmd, self.translate["to"], 2)
			pos, level, theName = self.check_if_float(cmd)
			if pos == -1:
				self.stats_good(False, "pulse no number")
				if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_heat '{cmd_in}' no number")
				return True
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_heat '{dev.name}' level {level}")

		else:
			cmd = cmd_in[pos+len(self.translate["heat"]):].strip()
			cmd = self.remove_firstword(cmd, "temp")
				
			cmd = self.strip_words(cmd, ["celsius","fahrenheit","degrees","degree","deg","grad","temperature","temperatur"])
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_cool-1 {cmd}")
			cmd = self.remove_word(cmd, self.translate["of"])
			cmd = self.remove_lastword(cmd, "cel", 1)
			cmd = self.remove_lastword(cmd, "fahr", 1)
			cmd = self.remove_lastword(cmd, "deg", 2)
			cmd = self.remove_lastword(cmd, "temp", 2)
			cmd = self.remove_lastword(cmd, self.translate["to"], 2)
			pos, level, theName = self.check_if_float(cmd, first=1)
			if pos == -1:
				self.stats_good(False, "heat no number")
				if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_heat '{cmd_in}' no number")
				return True
	
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_heat-1  {cmd}")
			dev = self.check_if_match_devices(theName)
			if not dev:
				if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"handle_set_heat No device found matching '{theName}'")
				self.stats_good(False, "device not found")
				return True
				
		if  not self.check_if_property( dev, "heatSetpoint", "heat not available"): return True
		if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_set_heat dev '{dev.name}' to {level} º")

		try:
			indigo.thermostat.setHeatSetpoint(dev.id, value=level)
			self.stats_good(True, self.feedback_ok["heat"])
		except:
			self.indiLOG.log(20, f"handle_set_heat not executed")
			self.stats_good(False, "not executed")
		return True


	####-------------------------------------------------------------------------####
	def handle_set_cool(self, cmd_in: str) -> bool:
		# (set) cool <device> (to) xx 
		"""Handles a 'set cool <device> to <temp>' voice command, stripping temperature unit words, parsing the numeric setpoint and device name, then setting the thermostat's cool setpoint.

		Inputs:
		    cmd_in (str): the incoming normalized voice command text
		Outputs:
		    bool: False if the 'cool' keyword is absent, otherwise True after attempting to set the cool setpoint and recording stats
		"""
		pos = cmd_in.find(self.translate["cool"]+" ")
		if pos < 0: return False
		
		if self.device != []:
			dev = self.device[1]
			cmd = self.device[2]
			cmd = self.strip_words(cmd, ["celsius","fahrenheit","degrees","degree","deg","grad","temperature","temperatur"])
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_cool-1 {cmd}")
			cmd = self.remove_lastword(cmd, self.translate["of"])
			cmd = self.remove_word(cmd, self.translate["of"])
			cmd = self.remove_lastword(cmd, "cel", 1)
			cmd = self.remove_lastword(cmd, "fahr", 1)
			cmd = self.remove_lastword(cmd, "deg", 2)
			cmd = self.remove_lastword(cmd, "temp", 2)
			cmd = self.remove_lastword(cmd, self.translate["to"], 2)
			pos, level, theName = self.check_if_float(cmd)
			if pos == -1:
				self.stats_good(False, "cool no number")
				if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_cool '{cmd_in}' no number")
				return True
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_cool '{dev.name}' level {level}")

		else:
			cmd = cmd_in[pos+len(self.translate["cool"]):].strip()
			cmd = self.remove_firstword(cmd, "temp")
			cmd = self.strip_words(cmd, ["celsius","fahrenheit","degrees","degree","deg","grad","temperature","temperatur"])
			cmd = self.remove_word(cmd, self.translate["of"])
			cmd = self.remove_lastword(cmd, "cel", 1)
			cmd = self.remove_lastword(cmd, "fahr", 1)
			cmd = self.remove_lastword(cmd, "deg", 2)
			cmd = self.remove_lastword(cmd, "temp", 2)
			cmd = self.remove_lastword(cmd, self.translate["to"], 2)
			pos, level, theName = self.check_if_float(cmd, first=1)
			if pos == -1:
				self.stats_good(False, "cool no number")
				if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_cool '{cmd_in}' no number")
				return True
				
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_set_cool-1 {cmd}")
			dev = self.check_if_match_devices(theName)
			if not dev:
				if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"handle_set_cool No device found matching '{theName}'")
				self.stats_good(False, "device not found")
				return True

		if  not self.check_if_property( dev, "coolSetpoint", "cool not available"): return True
		if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_set_cool dev '{dev.name}' to {level} º")

		try:
			indigo.thermostat.setCoolSetpoint(dev.id, value=level)
			self.stats_good(True, self.feedback_ok["cool"])
		except:
			self.indiLOG.log(20, f"handle_set_cool not executed")
			self.stats_good(False, "not executed")
		return True


	####-------------------------------------------------------------------------####
	def handle_set_variable(self, cmd_in: str) -> bool:
		#   set variable <varname> to value
		"""Handles a 'set variable <varname> to <value>' voice command, resolving the target Indigo variable and the value, mapping spelled-out numbers to ints, and updating the variable's value.

		Inputs:
		    cmd_in (str): the incoming normalized voice command text
		Outputs:
		    bool: False if the 'set variable' phrase or the 'to' separator is absent, otherwise True after attempting the update and recording stats
		"""
		pos = cmd_in.find(self.translate["set"]+" "+self.translate["variable"]+" ")
		if pos < 0: return False

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
				self.stats_good(False, "variable not found")
				return True
	
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_set_variable update var '{var.name}' to {level}")
	
		level = self.map_to_int(value.strip()) # one --> 1
		try:
			indigo.variable.updateValue(var.name, value=str(level))
			self.stats_good(True, self.feedback_ok["set"])
		except:
			self.indiLOG.log(20, f"handle_set_variable not executed")
			self.stats_good(False, "not executed")
		return True
		

	####-------------------------------------------------------------------------####
	def handle_get_value(self, cmd_in: str) -> bool:
		#  command :=  get device xx state yy 
		#  command :=  get variable varname  
		"""Handles a 'get' voice query that reads back either a variable's value ('get variable <name>') or a device state ('get device <name> state <state>'), resolving the target and reporting the found value via stats feedback.

		Inputs:
		    cmd_in (str): the incoming normalized voice command text
		Outputs:
		    bool: False if the command does not start with the 'get' keyword, otherwise True after reporting the value or a not-found result
		"""
		pos = cmd_in.find(self.translate["get"]+" ")
		if pos != 0: return False
		if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_get_value var '{cmd_in}' pos {pos}")

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
					varName = cmd.split(self.translate["variable"]+" ")[1]
					var = self.check_if_match_variables(varName)
			if var:
				self.stats_good(True, var.value)
				if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_get_value var '{var.name}' value:{var.value}")
			else:
				if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_get_value var '{varName}' not found")
				self.stats_good(False, "variable not found")
			return True
			
			
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
				self.stats_good(False,"variable not found")
				return True
			state = state.strip()
			if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_get_value dev '{devName}' {state} ")
		for yy in dev.states:
			#if self.decideMyLog("Logic"): self.indiLOG.log(20, f"handle_get_value testing {xx} >{xx.lower()}< == >{state}< , { xx.lower() == state}")
			if self.normalize_indigo_for_match(yy) == state:
				try:
					value = str(dev.states[yy])
					self.stats_good(True, value)
					if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20, f"handle_get_value  {dev.name}  state:{value} found ")
				except:
					self.indiLOG.log(20, f"handle_get_value not executed")
					self.stats_good(False, "not executed")
				return True


		if self.decideMyLog("Logic"): self.indiLOG.log(20, f'handle_get_value  no state: "{state}" found ')
		self.stats_good(False, "no state found")
		return True


	# ==========================
	#  utils for parsing, comparison.. 
	# ==========================

	####-------------------------------------------------------------------------####
	def apply_PhraseMappings(self, p: str) -> str:
		"""Lowercases the given phrase and applies configured phrase substitutions from map_from_to, plus fixed normalizations of 'actionid:'/'deviceid:' style tokens into spaced forms.

		Inputs:
		    p (str): the input phrase to normalize via mappings
		Outputs:
		    str: the phrase with mappings applied, or the original input if empty/falsy
		"""
		if not p:
			return p
		s = p.lower()
		for bad in self.map_from_to:
			if bad in s:
				s = s.replace(bad, self.map_from_to[bad])
		for xx, yy in [["actionid:","action id:"], ["deviceid:", "device id:"], ["variable id:", "variable id:"]]:
			if xx in s: 
				s = s.replace(xx, yy)
		return s


	####-------------------------------------------------------------------------####
	def is_blocked_device_name(self, p: str) -> bool:
		"""Checks whether the given device name contains any configured blocked words (case-insensitive substring match).

		Inputs:
		    p (str): the device name to test against the blocked-words list
		Outputs:
		    bool: True if a blocked word is found in the name, otherwise False
		"""
		if not p:
			return False
		s = p.lower()	
		for test in  self.blocked_words:
			if test in s: return True
			
		return False


	####-------------------------------------------------------------------------####
	def check_if_time_tag_ok(self, test_in: str) -> (bool, str):
		"""Validates the leading time tag (seconds-since-epoch) on an incoming message, accepting it only if within the allowed time window; if time tags are not expected it strips any numeric prefix. Returns the validity flag and the message with the time tag removed.

		Inputs:
		    test_in (str): the incoming message whose first token may be a timestamp
		Outputs:
		    tuple: (bool ok, str remaining message); note the rejection branch at bad-number returns only False
		"""
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
			return False, ""
		
		dt = time.time() - messageTimeNumber
		if dt >  self.allow_delta_time:
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20, f"Ignoring '{test_in}'; time not in allowed window: {dt:.1f}")
			return False, test_in
			
		if self.decideMyLog("Logic"):self.indiLOG.log(20, f"accepted  '{test_in}'; time in allowed window: {dt:.1f}")
		
		return True, test_in[len(messageTime):].strip()


	## for indigo dev  var names and state names 
	####-------------------------------------------------------------------------####
	def normalize_indigo_for_match(self, p: str) -> str:
		"""Normalizes an Indigo device/variable/state name for matching by splitting camelCase into words, replacing slashes/underscores/hyphens with spaces, collapsing whitespace, and lowercasing.

		Inputs:
		    p (str): the Indigo name to normalize
		Outputs:
		    str: the normalized lowercased name, or empty string if input is None
		"""
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
	####-------------------------------------------------------------------------####
	def normalize_incoming(self, p: str) -> str:
		"""Normalizes an incoming command string by collapsing whitespace, applying phrase mappings via apply_PhraseMappings, and collapsing whitespace again.

		Inputs:
		    p (str): the incoming command text to normalize
		Outputs:
		    str: the normalized command string, or empty string if input is None
		"""
		if p is None:
			return ""
		# replace outsideLamp with outside lamp
		# replace outside_Lamp with outside lamp
		# replace outside-Lamp with outside lamp
		# replace outside- Lamp with outside lamp
		# replace bad strings with good  eg the bug --> debug if set 
		#s = re.sub(r'(?<!^)(?=[A-Z])', ' ', p).lower() # # abcDef -> abc def
		s = re.sub(r"\s+", " ", p).strip()# replace multiple white spaces with one blank and no blank at the end
		s =  self.apply_PhraseMappings(s)
		s = re.sub(r"\s+", " ", s)# replace multiple white spaces with one blank and no blank at the end
		return s.strip().lower()

	# find last number float
	####-------------------------------------------------------------------------####
	def check_if_float(self, cmd_in:str, first=0) ->[int,float,list]:
		"""Scans the words of a command string from the end toward a starting index, returning the first word that can be parsed as a float along with its position and the preceding text.

		Inputs:
		    cmd_in (str): command string to search for a numeric (float) word
		    first (int): lowest word index to search down to (default 0)
		Outputs:
		    tuple: (index, float number, preceding words string) or (-1, -1, original string) if none found
		"""
		cmd = cmd_in.split(" ")
		# search from back to "first word "
		for ii in range(len(cmd)-1,first-1,-1):
			indigo.server.log(f' ii:{ii}, cmd:{cmd[ii]}, cmd:{cmd_in}')
			number  = self.map_to_float(cmd[ii])
			if type(number) == type(" "): continue
			return  ii, number , " ".join(cmd[0:ii])
		return -1, -1, cmd_in

	# find last number int
	####-------------------------------------------------------------------------####
	def check_if_int(self, cmd_in:str, first=0) ->[int,float,list]:
		"""Scans the words of a command string from the end toward a starting index, returning the first word that can be parsed as an integer along with its position and the preceding text.

		Inputs:
		    cmd_in (str): command string to search for a numeric (int) word
		    first (int): lowest word index to search down to (default 0)
		Outputs:
		    tuple: (index, int number, preceding words string) or (-1, -1, original string) if none found
		"""
		cmd = cmd_in.split(" ")
		# search from back to "first word "
		for ii in range(len(cmd)-1,first-1,-1):
			number  = self.map_to_int(cmd[ii])
			if type(number) == type(" "): continue
			return  ii, number , " ".join(cmd[0:ii])
		return -1, -1, cmd_in

		# find number 
	####-------------------------------------------------------------------------####
	def map_to_int(self, level:str):
		"""Converts a word to an integer, first checking a number-word lookup table (e.g. spelled-out numbers) and otherwise attempting int() conversion; returns the original string if neither succeeds.

		Inputs:
		    level (str): word or number text to convert to an int
		Outputs:
		    int or str: the integer value, or the original string if not convertible
		"""
		retNumber = level
		if level in _mapNumbertextToInt:
			retNumber = _mapNumbertextToInt[level]
		else:
			try: retNumber = int(level)
			except: pass
		return retNumber


	####-------------------------------------------------------------------------####
	def map_to_float(self, level:str):
		"""Converts a word to a float by attempting float() directly, then falling back to converting via map_to_int; returns the original string if conversion fails.

		Inputs:
		    level (str): word or number text to convert to a float
		Outputs:
		    float or str: the float value, or the original string if not convertible
		"""
		try: 
			xx = float(level)
			return xx
		except: pass
		try:
			xx = float(map_to_int(level))
			return float(xx)
		except: pass
		return level			


	####-------------------------------------------------------------------------####
	def device_is_dimmable(self, dev) -> bool:
		"""Determines whether an Indigo device supports dimming by checking for a brightnessLevel or dimLevel entry in its states.

		Inputs:
		    dev (indigo.Device): device to test for dimmable states
		Outputs:
		    bool: True if the device has a brightness/dim state, False otherwise or on error
		"""
		try:
			return ("brightnessLevel" in dev.states) or ("dimLevel" in dev.states)
		except Exception:
			return False


	####-------------------------------------------------------------------------####
	def check_if_match_devices(self, theName: str):
		
		"""Resolves a spoken name to an Indigo device by exact match, then by normalized substring match against device names, then via a configured synonyms-to-device-id mapping; returns None if blocked or unmatched.

		Inputs:
		    theName (str): device name (or synonym) to match
		Outputs:
		    indigo.Device or None: the matched device, or None if blocked or no match found
		"""
		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"check_if_match_device  {theName}")

		if self.is_blocked_device_name(theName): return None
		
		if theName in indigo.devices:
			return indigo.devices[theName]
			
		for dev in indigo.devices:
			indigoName = self.normalize_indigo_for_match(dev.name)
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


	####-------------------------------------------------------------------------####
	def check_if_match_variables(self, theName):
		"""Resolves a spoken name to an Indigo variable by exact match, then by normalized substring match against variable names, then via a configured synonyms-to-variable-id mapping; returns None if blocked or unmatched.

		Inputs:
		    theName (str): variable name (or synonym) to match
		Outputs:
		    indigo.Variable or None: the matched variable, or None if blocked or no match found
		"""
		if self.decideMyLog("Logic"): self.indiLOG.log(20, f"check_if_match_variables  {theName}")
	
		if self.is_blocked_device_name(theName): return None

		if theName in indigo.variables:
			return indigo.variables[theName]

		for var in indigo.variables:
			indigoName = self.normalize_indigo_for_match(var.name)
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

	####-------------------------------------------------------------------------####
	def check_if_property(self, dev, prop: str, errText:str) -> bool:
		"""Checks whether a given property key exists on a device (treated as a dict); if missing, logs the error text and records a failure in the stats.

		Inputs:
		    dev (indigo.Device): device whose properties are checked
		    prop (str): property key to look for
		    errText (str): message to log and record if the property is absent
		Outputs:
		    bool: True if the property exists, False otherwise
		"""
		theDict = dict(dev) 
		#indigo.server.log(f'check_if_property dict: {theDict}')
		if prop in theDict:
			return True
		else:
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20, errText)
			self.stats_good(False, errText)
			return False


	####-------------------------------------------------------------------------####
	def word_number(self, cmd_in:str, word_to_find:str) -> [int, int, list]:
		# remove only phrase that have space before
		"""Locates a target word (preceded by a space) within a command string, scanning words from the end, and returns its index, the total word count, and the split word list.

		Inputs:
		    cmd_in (str): command string to search
		    word_to_find (str): word to locate within the command
		Outputs:
		    tuple: (index, word count, word list) if found, else (-1, 0, original string)
		"""
		if cmd_in.find(" "+word_to_find) < 0: return -1, 0, cmd_in
		cmd = cmd_in.split(" ")
		for ii in range(len(cmd)-1,-1,-1):
			if cmd[ii].find(word_to_find) > -1:
				return ii, len(cmd), cmd
		return -1, 0, cmd_in


	####-------------------------------------------------------------------------####
	def remove_firstword(self, cmd_in:str, word_to_remove:str) -> str:
		"""Removes the first word of a command string if it starts with the given word, returning the remaining text; otherwise returns the command unchanged.

		Inputs:
		    cmd_in (str): command string to trim
		    word_to_remove (str): word expected at the start of the command
		Outputs:
		    str: the command with its first word removed, or the original string
		"""
		split_cmd = cmd_in.split()
		if split_cmd[0].find (word_to_remove) == 0:
			return " ".join(split_cmd[1:])
		return cmd_in


	####-------------------------------------------------------------------------####
	def remove_lastword(self, cmd_in:str, word_to_remove:str, last_word_pos:int) -> str:
		"""Removes an occurrence of a word from a command string only when it appears near the end (within last_word_pos of the final word), using word_number to locate it; otherwise returns the command unchanged.

		Inputs:
		    cmd_in (str): command string to trim
		    word_to_remove (str): word to remove if positioned near the end
		    last_word_pos (int): how far from the last word the word must be to qualify for removal
		Outputs:
		    str: the command with the word removed, or the original string if conditions are not met
		"""
		pos, nwords, split_cmd = self.word_number(cmd_in, word_to_remove)
		if pos < 0: 						return cmd_in
		if nwords < 2: 						return cmd_in
		if nwords - last_word_pos < pos:	return cmd_in
		split_cmd.pop(pos)
		return " ".join(split_cmd)


	####-------------------------------------------------------------------------####
	def remove_word(self, cmd_in:str, word_to_remove:str, minPos=0) -> str:
		# remove only phrase that have space before and after 
		"""Removes a word that is surrounded by spaces from a command string, but only if it occurs at or beyond a minimum position; returns the trimmed string or the original if not found before that position.

		Inputs:
		    cmd_in (str): command string to trim
		    word_to_remove (str): word (space-delimited) to remove
		    minPos (int): minimum character position the word must be at to be removed (default 0)
		Outputs:
		    str: the command with the word removed and stripped, or the original string
		"""
		pos = cmd_in.find(" "+word_to_remove+" ")
		if pos < minPos: return cmd_in
		cmd = cmd_in.split(" "+word_to_remove+" ")
		cmd = " ".join(cmd)
		return  cmd.strip(" ")


	####-------------------------------------------------------------------------####
	def strip_words(self, cmd_in, word_to_strip) -> str:
		"""Strips a set of trailing words from a command string, removing each given word from the right end and trimming surrounding whitespace.

		Inputs:
		    cmd_in (str): the command string to clean
		    word_to_strip (list): iterable of words to strip from the end
		Outputs:
		    str: the command with trailing words and whitespace removed
		"""
		cmd = cmd_in.rstrip()
		for word in word_to_strip:
			cmd = cmd.rstrip(word).rstrip()
		return  cmd.strip()

	
	####-------------------------------------------------------------------------####
	def set_feedback_value_ok(self, value_in:str):
		"""Sets self.feedback_value for a successful command according to the configured return_feedback mode (none, detailed, or simple), using the supplied value or a default 'ok'/return_ok string.

		Inputs:
		    value_in (str): feedback text to use, or empty string for a default
		Outputs:
		    None: updates self.feedback_value
		"""
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


	####-------------------------------------------------------------------------####
	def set_feedback_value_bad(self, value_in:str):
		"""Sets self.feedback_value for a failed command according to the configured return_feedback mode (detailed, simple, or none), using the supplied value or a default 'not executed' string.

		Inputs:
		    value_in (str): feedback text to use, or empty string for a default
		Outputs:
		    None: updates self.feedback_value
		"""
		if self.return_feedback == "detailed":
			if value_in != "":	self.feedback_value = value_in
			else:				self.feedback_value = "not executed"
		elif self.return_feedback == "simple":
								self.feedback_value = "not executed"
		else:
								self.feedback_value = " "
								
	####-------------------------------------------------------------------------####
	def split_compound(self, cmd: str) -> str:
		"""Splits a command string into a list of sub-commands on the separators ' and ', ' then ', or '&', returning the original string unchanged if none are present.

		Usage note (original):
		    Split on 'and' / 'then' / '&' with spaces.
		    Example: 'unmute tv and set tv to 24' -> ['unmute tv', 'set tv to 24']

		Inputs:
		    cmd (str): the command string to split
		Outputs:
		    list or str: list of sub-command strings if a separator was found, otherwise the original string
		"""
		if not cmd:					return cmd
		if " and " in cmd:			return cmd.split(" and ")
		if " then " in cmd:			return cmd.split(" then ")
		if "&" in cmd:				return cmd.split("&")
		return cmd


	####-------------------------------------------------------------------------####
	def stats_good(self, good: bool, retText):
		"""Records the success or failure of a command by updating the appropriate feedback variable, appending a timestamp to the ok_commands or failed_commands dictionary, and persisting that dictionary to a JSON file.

		Usage note (original):
		    write out success fail to json and send back message to iphne

		Inputs:
		    good (bool): True if the command succeeded, False if it failed
		    retText (str): feedback text to report back for detailed mode
		Outputs:
		    None: updates feedback variables, command-history dicts, and writes JSON files
		"""
		pos = self.raw.find(" ")
		cmdOnly = self.raw[pos+1:].strip() # no time stamp 
		self.finished = True
				
		if not good:
			if cmdOnly not in self.failed_commands:
				self.failed_commands[cmdOnly] = []
			self.set_feedback_value_bad(retText)
			if self.return_feedback == "simple":
				indigo.variable.updateValue(self.var_name_feedback, value="not executed")
			elif self.return_feedback == "detailed":
				indigo.variable.updateValue(self.var_name_feedback, value=retText)
			self.failed_commands[cmdOnly].append( datetime.datetime.now().strftime(_defaultDateStampFormat))
			self.writeJson(self.failed_commands, fName=self.indigoPreferencesPluginDir + "failed_commands.json")
		else:
			self.set_feedback_value_ok(retText)
			if self.return_feedback == "simple":
				indigo.variable.updateValue(self.var_name_feedback, value="ok")
			elif self.return_feedback == "detailed":
				indigo.variable.updateValue(self.var_name_feedback, value=retText)

			if cmdOnly not in self.ok_commands:
				self.ok_commands[cmdOnly] = []
			self.ok_commands[cmdOnly].append( datetime.datetime.now().strftime(_defaultDateStampFormat))
			self.writeJson(self.ok_commands, fName=self.indigoPreferencesPluginDir + "ok_commands.json")
		return 	


	####-----------------	 ---------
	def decideMyLog(self, msgLevel: int) -> bool:
		"""Decides whether a log message of the given level/area should be emitted, based on the plugin's configured debugAreas (returning True if 'All' is enabled or the area matches).

		Inputs:
		    msgLevel (str): the log level/area key to test against enabled debug areas
		Outputs:
		    bool: True if the message should be logged, otherwise False
		"""
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
	####-------------------------------------------------------------------------####
	def __init__(self, fmt=None, datefmt=None, level_fmts={}, level_date={}):
		"""Initializes a LevelFormatter logging formatter, building a per-level logging.Formatter (with matching date format) for each level in level_fmts and storing a default format/datefmt on the base class.

		Inputs:
		    fmt (str or None): default log format string
		    datefmt (str or None): default date format string
		    level_fmts (dict): mapping of log level to format string
		    level_date (dict): mapping of log level to date format string
		Outputs:
		    None: initializes the formatter instance
		"""
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
		"""Formats a log record using the per-level formatter registered for its level number, falling back to the base Formatter's default formatting when no level-specific formatter exists.

		Inputs:
		    record (logging.LogRecord): the log record to format
		Outputs:
		    str: the formatted log message string
		"""
		if record.levelno in self._level_formatters:
			return self._level_formatters[record.levelno].format(record)

		return super(LevelFormatter, self).format(record)

