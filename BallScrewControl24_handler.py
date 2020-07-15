############################
# **** IMPORT SECTION **** #
############################
import sys
import os
import linuxcnc

from PyQt5 import QtCore, QtWidgets

#from qtvcp.widgets.mdi_line import MDILine as MDI_WIDGET
#from qtvcp.widgets.gcode_editor import GcodeEditor as GCODE
#from qtvcp.lib.keybindings import Keylookup
from qtvcp.core import Status, Action

# Set up logging
#from qtvcp import logger
#LOG = logger.getLogger(__name__)

# Set the log level for this module
#LOG.setLevel(logger.INFO) # One of DEBUG, INFO, WARNING, ERROR, CRITICAL

###########################################
# **** INSTANTIATE LIBRARIES SECTION **** #
###########################################

KEYBIND = Keylookup()
STATUS = Status()
ACTION = Action()
###################################
# **** HANDLER CLASS SECTION **** #
###################################

class HandlerClass:

    ########################
    # **** INITIALIZE **** #
    ########################
    # widgets allows access to  widgets from the qtvcp files
    # at this point the widgets and hal pins are not instantiated
    def __init__(self, halcomp,widgets,paths):
        #self.hal = halcomp
        self.w = widgets
        self.PATHS = paths

    ##########################################
    # SPECIAL FUNCTIONS SECTION              #
    ##########################################

    # at this point:
    # the widgets are instantiated.
    # the HAL pins are built but HAL is not set ready
    # This is where you make HAL pins or initialize state of widgets etc
    def initialized__(self):
        pass
        
    def onBtnNext(self):
        print "*** onBtnNext clicked"
        
        self.close()

################################
# required handler boiler code #
################################

def get_handlers(halcomp,widgets,paths):
     return [HandlerClass(halcomp,widgets,paths)]