#!/usr/bin/python
# -*- coding: utf-8 -*-

############################
# **** IMPORT SECTION **** #
############################
# стандартные пакеты
import sys, os

# пакеты linuxcnc
import linuxcnc, hal, hal_glib

# пакеты интерфейса
from PyQt5 import QtCore, QtWidgets
#from qtvcp.widgets import FocusOverlay
from qtvcp.widgets.mdi_line import MDILine as MDI_WIDGET
from qtvcp.widgets.gcode_editor import GcodeEditor as GCODE
from qtvcp.lib.keybindings import Keylookup
from qtvcp.core import Status, Action

# пакеты для графиков
import pyqtgraph as pg
from pyqtgraph import PlotWidget, plot

# пакет для xlsx
import openpyxl

# Set up logging
from qtvcp import logger
LOG = logger.getLogger(__name__)

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
        self.hal = halcomp
        self.w = widgets
        self.PATHS = paths
        
        self.siggen_test_read_pin = self.hal.newpin('siggen_test_read_pin',hal.HAL_FLOAT, hal.HAL_IN) # тестовый пин для получения синусоиды с siggen http://linuxcnc.org/docs/2.8/html/hal/halmodule.html#_use_with_hal_glib_in_qtvcp_handler
        
        self.siggen_test_read_pin.value_changed.connect(lambda s: self.on_siggen_test_read_pin_value_changed(s)) # connect the pin to a callback http://linuxcnc.org/docs/2.8/html/hal/halmodule.html#_use_with_hal_glib_in_qtvcp_handler


    ##########################################
    # SPECIAL FUNCTIONS SECTION              #
    ##########################################

    # at this point:
    # the widgets are instantiated.
    # the HAL pins are built but HAL is not set ready
    # This is where you make HAL pins or initialize state of widgets etc
    def initialized__(self):
        database_file = 'База данных испытаний.xlsx'
        try:
            wb = openpyxl.load_workbook(filename = database_file, read_only = True)
            print("*** OK load_workbook")
            for sheet in wb:
                print(sheet.title)
            ws = wb[wb.sheetnames[1]]
            print("*** OK wb[\"Modeli\"]")
            list_test_types = []
            row = 1
            print("*** OK value 1", ws.cell(row = 1, column = 1).value)
            print("*** OK value 2", ws.cell(row = 2, column = 1).value)
            print("*** OK value 3", ws.cell(row = 3, column = 1).value)
            
            while(ws.cell(row = row, column = 1).value is not None):
                list_test_types.append(ws.cell(row = row, column = 1).value)
                print("*** OK row=", row, " appended, value = ", ws.cell(row = row, column = 1).value)
                row = row + 1
            print("*** list_test_types = ", list_test_types) 
            self.w.cmbModel.addItems(list_test_types)
            print("*** OK ", addItems)
        except:
            print("*** Не удалось открыть файл базы данных \"", database_file, "\"")
            #fov = FocusOverlay(self)
            #fov.show()
            pass
        
    ########################
    # CALLBACKS FROM STATUS#
    ########################

    #######################
    # CALLBACKS FROM FORM #
    #######################
    
    def onBtnNext(self):
        print "*** onBtnNext clicked"
        if(self.w.cmbTestType.currentIndex()<4):
            self.w.stackedWidget.setCurrentIndex(self.w.cmbTestType.currentIndex()+1)
        else:
            self.w.stackedWidget.setCurrentIndex(3)
        # self.close() только для случая многооконного интерфейса
    
    def onBtnTempShow1(self):
        self.w.stackedWidget.setCurrentIndex(0)
        pass
        
    def onBtnTempShow21(self):
        self.w.stackedWidget.setCurrentIndex(1)
        pass
        
    def onBtnTempShow22(self):
        self.w.stackedWidget.setCurrentIndex(2)
        pass
        
    def onBtnTempShow23(self):
        self.w.stackedWidget.setCurrentIndex(3)
        pass
        
    def onBtnTempShow24(self):
        self.w.stackedWidget.setCurrentIndex(4)
        pass
        
    def onBtnTempShow31(self):
        self.w.stackedWidget.setCurrentIndex(5)
        pass
        
    def onBtnTempShow32(self):
        self.w.stackedWidget.setCurrentIndex(6)
        pass
        
    def onBtnTempShow33(self):
        self.w.stackedWidget.setCurrentIndex(7)
        pass
        
    def onBtnTempShow34(self):
        self.w.stackedWidget.setCurrentIndex(8)
        pass

    #####################
    # GENERAL FUNCTIONS #
    #####################
    
    def on_siggen_test_read_pin_value_changed(self,data):
        print("*** siggen pin data: ", data)
        print("*** siggen pin: ", self.siggen_test_read_pin.get())
        print("*** siggen.0.sine directly", hal.get_value("siggen.0.sine"))
    
################################
# required handler boiler code #
################################

def get_handlers(halcomp,widgets,paths):
     return [HandlerClass(halcomp,widgets,paths)]