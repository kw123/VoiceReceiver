#! /Library/Frameworks/Python.framework/Versions/Current/bin/python3
# -*- coding: utf-8 -*-
####################
# voice receiver Plugin
# Developed by Karl Wachs
# karlwachs@me.com

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


######### set new  pluginconfig defaults
# this needs to be updated for each new property added to pluginProps. 
# indigo ignores the defaults of new properties after first load of the plugin 
kDefaultPluginPrefs = {
	"MSG":									"please enter values",
	"expect_time_tag":						True,
	"allow_delta_time":						30.,
	"var_name":								"voice_command_text",
	"folder_name":							"voiceReceiver",
	"blocked_device_words":					"alarm|lock",
	"use_fragments_to_dermine_device":			False,
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

			self.synonymes_for_actions  = self.readJson(self.indigoPreferencesPluginDir+"synonymes_for_actions.json", defReturn={})

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

			self.folder_name = self.pluginPrefs.get("folder_name", kDefaultPluginPrefs["folder_name"])	
			try:    indigo.variables.folder.create(self.folder_name)
			except: pass

			self.var_name = self.pluginPrefs.get("var_name", kDefaultPluginPrefs["var_name"])	
			try:    indigo.variable.create(var_name,  "", self.folder_name)
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
	def blockWordsCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20,f"blockWordsCallback {valuesDict}")
		self.blocked_device_words = valuesDict["blocked_device_words"].split("|")
		self.writeJson({"blocked_device_words":self.blocked_device_words}, fName=self.indigoPreferencesPluginDir + "blocked_device_words.json", sort = True, doFormat=True, singleLines= False )


	####-----------------  ---------
	def addFromCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20,f"selectActionsCallback {valuesDict}")
		bad = valuesDict["from"]
		good = valuesDict["to"]
		if bad not in self.map_from_to:
			self.map_from_to[bad] = good
		self.writeJson(self.map_from_to, fName=self.indigoPreferencesPluginDir + "map_from_to.json", sort = True, doFormat=True, singleLines= False )

	####-----------------  ---------
	def addFromCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20,f"selectActionsCallback {valuesDict}")
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
		self.indiLOG.log(20,f"removeFromCallback {bad}  {self.map_from_to}")
		self.writeJson(self.map_from_to, fName=self.indigoPreferencesPluginDir + "map_from_to.json", sort = True, doFormat=True, singleLines= False )


####-------------------------------------------------------------------------####
	def filterFromTo(self, filter="", valuesDict=None , typeId=None):
		xList = []
	
		for bad in self.map_from_to:
			xList.append([bad, bad])
		#self.indiLOG.log(20,f"filterWords xList: {xList}")
		return xList


	####-----------------  ---------
	def addActionsCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20,f"selectActionsCallback {valuesDict}")
		if self.actionNumber == 0: return 
		actionId = int(valuesDict["actionadd"])

		definedAction = indigo.actionGroups[actionId].name
		self.actions[definedAction] = [actionId, self.actionNumber]
		#self.indiLOG.log(20,f"selectActionsCallback actionId:  {actionId}, :{definedAction}, {self.actions}")
				
					
		self.writeJson(self.actions, fName=self.indigoPreferencesPluginDir + "actions.json", sort = True, doFormat=True, singleLines= False )


	####-----------------  ---------
	def delActionsCallback(self, valuesDict=None , typeId=""):
		s#elf.indiLOG.log(20,f"delActionsCallback {valuesDict}")
		if self.actionNumber == 0: return 
		
		delAction = -1
		for definedAction in self.actions:
			if self.actions[definedAction][1] == self.actionNumber: #already defined, keep
				delAction = definedAction
				break
				
		#self.indiLOG.log(20,f"delActionsCallback  actionNumber: {self.actionNumber}, delAction:{delAction},")
		if delAction == -1: return 
		del self.actions[definedAction]
		self.writeJson(self.actions, fName=self.indigoPreferencesPluginDir + "actions.json", sort = True, doFormat=True, singleLines= False )



	####-----------------  ---------
	def defineSynonymActionCallback(self, valuesDict=None , typeId=""):
		#self.indiLOG.log(20,f"selectActionsCallback {valuesDict}")
		actionId = valuesDict["action"]
		synonym = valuesDict["synonymAdd"]
		if synonym not in self.synonymes_for_actions:
			self.synonymes_for_actions[synonym] = actionId
		self.writeJson(self.synonymes_for_actions, fName=self.indigoPreferencesPluginDir + "synonymes_for_actions.json", sort = True, doFormat=True, singleLines= False )


	####-----------------  ---------
	def removeSynonymActionCallback(self, valuesDict=None , typeId=""):
		s#elf.indiLOG.log(20,f"selectActionsCallback {valuesDict}")
		synonym = valuesDict["synRemove"]
		if synonym in self.synonymes_for_actions:
			del self.synonymes_for_actions[synonym]
		self.writeJson(self.synonymes_for_actions, fName=self.indigoPreferencesPluginDir + "synonymes_for_actions.json", sort = True, doFormat=True, singleLines= False )


	####-----------------  ---------
	def actionNumberConfirmCallback(self, valuesDict=None, typeId=""):
		self.actionNumber = int(valuesDict["actionNumber"])
		self.actionId = 0


	
####-------------------------------------------------------------------------####
	def filterSynonymesActions(self, filter="", valuesDict=None , typeId=None):
		xList = []
	
		for syn in self.synonymes_for_actions:
			xList.append([syn, syn])
		#self.indiLOG.log(20,f"filterSynonymes xList: {xList}")
		return xList
	
####-------------------------------------------------------------------------####
	def filternumbers_1_100(self, filter="", valuesDict=None , typeId=None):
		xList = []
	
		for ii in range(1,100):
			xList.append([ii, ii])
		return xList

	

	
####-------------------------------------------------------------------------####
	def filterActions(self, filter="", valuesDict=None , typeId=None):
		xList = []
		
		UiValuesDict = valuesDict.get("UiValuesDict",{})
		#self.indiLOG.log(20,f"filterActions {filter}, {UiValuesDict}")
		#self.indiLOG.log(20,f"filterActions {self.actions}")
		
		if self.actionNumber == 0: return xList

		filt = int(filter)
		
		if filt  == -1:
			for action in self.actions:
				xList.append([self.actions[action][0], action])
			return xList

		if filt == 2:
			for action in self.actions:
				nn = self.actions[action][1]
				if nn == self.actionNumber:
					xList.append(["0",action])
					break
			#self.indiLOG.log(20,f"filterActions {xList}")
			return xList


		for action in indigo.actionGroups.iter(self.pluginId):
			name = action.name
			actionN = action.id
			#self.indiLOG.log(20,f"action: {name}, {actionN}")
			if name not in self.actions:
				xList.append([action.id, name])
				continue
							
		#self.indiLOG.log(20,f"filterActions xList: {xList}")
		return xList


	####-----------------	 ---------
	def printConfig(self,  valuesDict=None , typeId=""):
		try:
			out =  "\n"
			out += " credit must go to @ditch on the indigo forum who came up with the script\n "
			out =  "\n"
			out =  "What does it do?\n"
			out =  "  receives message in varibale from iphone dictation shortcut \n"
			out =  "  analyses the received string to look for commands to \n"
			out =  "       start indigo actions (must be defined in menu)\n"
			out =  "       switch on/off or dim devices \n"
			out =  "\n"
			out =  "\n"
			out += '================================ INSTALL ===========================\n'
			out += 'To install correctly: \n'
			out += 'Create shortcut on iPhone with the following items:\n'
			out += '1. Dismiss Siri and Continue                                         to shorten pause \n'
			out += '2. Dictate text                                                      this is where the voice gets recorded\n'
			out += '3. Current Date                                                      create date object  \n'
			out += '3. Get Seconds between 1970-01-01 0:00 z and Date                    create epoch time in secs  \n'
			out += '4. Text "Time Between Dates" "Dictated Text"                         create text string to be send timestamp space command\n'
			out += '5. Get contents of https://<yourid>indigodome.net/v2/api/command     indigo contact  \n'
			out += '6a.   method Post\n'
			out += '6b.   Headers\n'
			out += '6b1.    Authorization  Bearer <your id string> 						 from indigo web page \n'
			out += '6b2.    Content-Type applicatio/json\n'
			out += '6b3.    Request Body: JSON\n'
			out += '6b3a.     message : Text indigovariable.updateValue\n'
			out += '6b3a.     objectId : <indigo variable id>                            here you put the indigo variable id\n'
			out += '6b3a.     parameters : Dictionary\n'
			out += '6b3a1.      value  Text: Text                                        this is the varibale that contains time space command\n'
			out += '7. name it eg "indigo" \n'
			out += '8. share to desktop\n'
			out += '9. save\n'
			out += '10.  if you have a light named office lights:  \n'
			out += '10.  speaking "hey Siri Indigo" pause "turn on office lights"  \n'
			out += '10.  should turn on office lights  \n'
			out += '\n'
			out += '  command examples  \n'
			out += '   turn on/off device_name  \n'
			out += '   set device to xx percent  (xx = 0..100)\n'
			out += '   device_name to xx    (xx = 0..100)\n'
			out += '   action_name  (name and action id must be set in menu)  \n'
			out += '   device_name to xx and action_name and device2_name on    will execute 3 commands  \n'
			out += ' upper and lower cases in commands are ignored\n'
			out += '\n'
			out += 'in menue you can define:\n'
			out += '1. action names and ids to be executed \n'
			out += '2. mappings of bad to good words (eg lamp to lights)  the plugin will replace the bad strings with the good\n'
			out += '\n'
			out += '\n'
			out += "\n =============plugin config Parameters========\n"
			out += f"allow_delta_time     =  {self.allow_delta_time}\n"
			out += "                         message must not be older thn current timestamp +  allow_delta_time\n\n"
			out += f"expect_time_tag      =  {self.expect_time_tag}\n"
			out += "                         require time stamp value as first work in message\n\n"
			out += f"use fragments        =  {self.use_fragments_to_dermine_device}\n"
			out += "                         allow plugin to try to figure out which device was mean if not 100 % match using fragments\n\n"
			out += f"var_name             =  {self.var_name}\n"
			out += "                         name of the variable the plugin will listen to, will be created if it does not exist\n\n"
			out += f"folder_name          =  {self.folder_name}\n"
			out += "                         folder name of the variable, will be created if it does not exist\n\n"
			out += f"blocked_device_words =  {self.blocked_device_words}\n"
			out += "                         words that are not allowed for devices and actions eg alarm\n\n"
			out += f"actions              =  {self.actions}\n"
			out += "                         indigo action names and indigo ids, using {indigo action name:[indigo action id, seq number]} }\n\n"
			out += f"synonymes Action     =  {self.synonymes_for_actions}\n"
			out += "                         voice action names and  indigo action ids, using {voice action string:indigo action id}  \n\n"
			out += f"map_from_to          =  {self.map_from_to}\n"
			out += "                         bad words to be replaced by good words  using {map voice string : to string to be used} \n\n"
			out += "                          eg dor : door  \n\n"
			out += "                          or tür : door (for the germans)  \n\n"
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
			if self.decideMyLog("ReceivdeData"): self.indiLOG.log(20,f"orig_var '{new_var.value}'")
				
	
			raw = new_var.value
	
			if self.decideMyLog("ReceivdeData"):	self.indiLOG.log(20,f"Command received raw: '{raw}'")
	
			if not raw or not raw.strip():
				return
	
			raw_stripped = raw.strip()
	
			ok, raw_stripped = self.check_if_time_tag_ok(raw_stripped)
			if not ok: return 
	
			if self.decideMyLog("ReceivdeData"): self.indiLOG.log(20,f"Command received raw, tags removed: '{raw_stripped}'")
	
			cmd =  self.normalize_command(raw_stripped)
			cmdLower = cmd.lower()
			
			if self.decideMyLog("ReceivdeData"):	self.indiLOG.log(20,f"Normalized command: '{cmd}'")
	
			if cmdLower == "what can you do":
				self.log_available_commands()
				return
	
			elif cmdLower == "list devices":
				self.log_devices()
				return
	
			elif cmdLower == "test":
				self.indiLOG.log(20,f"received test command: '{cmd}'")
				return
	
	
			# Compound support: run each sub-command in order
			sub_cmds =  self.split_compound(cmd)
			if len(sub_cmds) > 1:
					if self.decideMyLog("all"):	self.indiLOG.log(20,f"Compound command -> {sub_cmds}")
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
			if self.decideMyLog("BadMessage"):	self.indiLOG.log(20,f"Ignoring '{test}'; bad time info, not a number")
			return
		
		dt = time.time() - messageTimeNumber
		if dt >  self.allow_delta_time:
			if self.decideMyLog("BadMessage"):	self.indiLOG.log(20,f"Ignoring '{test}'; time not in allowed window: {dt:.1f}")
			return False, ""
			
		if self.decideMyLog("Logic"):self.indiLOG.log(20,f"accepted  '{test}'; time in allowed window: {dt:.1f}")
		
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
				if self.decideMyLog("Logic"): self.indiLOG.log(20,f"find_device_by_name_fragment: use perfect match device: '{fragment}'")
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
				if self.decideMyLog("Logic"): self.indiLOG.log(20,f"multiple devices match '{fragment}': {names}{suffix}")
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
		self.indiLOG.log(20,"Available commands:")
		for cmd in sorted( self.actions.keys()):
			self.indiLOG.log(20,f"  Indigo, {cmd}")
	
	def log_devices(self):
		self.indiLOG.log(20,"Device list (name → normalized) [truncated if large]:")
		count = 0
		for dev in indigo.devices:
			if count >=  self.LIST_DEVICES_MAX:
				self.indiLOG.log(20,f"... truncated at {LIST_DEVICES_MAX} devices ...")
				break
			self.indiLOG.log(20,f"   {dev.name} → {normalize_name_for_match(dev.name)}")
			count += 1
	
	
	# ==========================
	#  ACTION EXECUTION
	# ==========================
	
	def device_is_dimmable(self, dev) -> bool:
		try:
			return ("brightnessLevel" in dev.states) or ("dimLevel" in dev.states)
		except Exception:
			return False
	
	def handle_set_level(self, device_phrase: str, level: int) -> bool:
		device_phrase = self.normalize_device_phrase(device_phrase)
		dev = self.find_device_by_name_fragment(device_phrase)
		if not dev:
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20,f"No device found matching '{device_phrase}'")
			return False

		level = max(0, min(100, int(level)))

		if self.device_is_dimmable(dev):
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20,f"Setting '{dev.name}' to {level}%")
			try:
				indigo.dimmer.setBrightness(dev.id, value=level)
			except	Exception as e:
				if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
			return True

		# relay fallback: >0 => ON, 0 => OFF
		if level == 0:
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20,f"Setting '{dev.name}' to 0% (relay -> OFF)")
			try:
				indigo.device.turnOff(dev.id)
			except Exception as e:
				self.indiLOG.log(20,f"Error turning off '{dev.name}': {e}")
		else:
			if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20,f"Setting '{dev.name}' to {level}% (relay -> ON)")
			try:
				indigo.device.turnOn(dev.id)
			except	Exception as e:
				if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		
			return True
	
	def handle_turn_on_off(self, device_phrase: str, state: str) -> bool:
		device_phrase = self.normalize_device_phrase(device_phrase)
		dev = self.find_device_by_name_fragment(device_phrase)
		if not dev:
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20,f"No device found matching '{device_phrase}'")
			return False

		if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20,f"Turning {state} '{dev.name}'")

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
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		return True
	
	def try_pattern_commands(self, cmd: str) -> bool:
		try:
			state = "none"
			cmd = re.sub(r"\s+", " ", cmd.strip())
			if self.decideMyLog("Logic"):		self.indiLOG.log(20,f"try_pattern_commands {cmd} ")
	
			m = re.match(r"^turn\s+(on|off)\s+(?:the\s+)?(.+)$", cmd)
			if m:
				if self.decideMyLog("Logic"):	self.indiLOG.log(20,f"try_pattern_commands onOff  m:{m.groups()}")
				return  self.handle_turn_on_off(m.group(2).strip(), m.group(1))
	
			m = re.match(r"^(?:turn\s+)?(.+?)\s+(on|off)$", cmd)
			if m:
				if self.decideMyLog("Logic"):	self.indiLOG.log(20,f"try_pattern_commands 2   m:{m.groups()}")
				return  self.handle_turn_on_off(m.group(1).strip(), m.group(2))
	
			# VERB LEVEL FIRST (so "brighten/dim ..." doesn't get swallowed)
			m = re.match(r"^(\w+)\s+(.+?)\s+to\s+(\d+)\s*(?:%|percent)?$", cmd)
			if m:
				if self.decideMyLog("Logic"):	self.indiLOG.log(20,f"try_pattern_commands 3  m:{m.groups()}")
				verb = m.group(1).lower()
				device_phrase = m.group(2).strip()
				level = int(m.group(3))
	
				if verb.startswith("bright"):
					return  self.handle_set_level(device_phrase, level)
	
				if verb in ("dim", "darken"):
					return  self.handle_set_level(device_phrase, level)
	
			# LEVEL: "set" is optional; percent marker is optional (% or the word "percent")
			# Examples:
			#   set den lamp to 60%
			#   den lamp to 60
			#   den lamp to 60 percent
			m = re.match(r"^(?:set\s+)?(.+?)\s+to\s+(\d+)\s*(?:%|percent)?$", cmd)
			if m:
				if self.decideMyLog("Logic"):	self.indiLOG.log(20,f"try_pattern_commands 4   m:{m.groups()}")
				return self.handle_set_level(m.group(1).strip(), int(m.group(2)))
	
			return False
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
	
	def execute_actions_for_command(self, cmd: str):
	
		isSynonym = self.synonymes_for_actions.get(cmd, 0)
		actionInfo = False

		if isSynonym !=0:
			for action in self.actions:
				if isSynonym == self.actions[action][0]: # == indigo id
					actionInfo = self.actions[action]
					break
					
		if not actionInfo:
			actionInfo = self.actions.get(cmd, False)
			
		if not actionInfo:
			if self.try_pattern_commands(cmd):
				return
			if self.decideMyLog("BadMessage"): self.indiLOG.log(20,f"No match for '{cmd}' in ACTIONs or patterns")
			return

		if self.decideMyLog("UpdateIndigo"): self.indiLOG.log(20,f"Matched command '{cmd}' → action groups {actionInfo}")
		try:
			indigo.actionGroup.execute(actionInfo[0])
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


