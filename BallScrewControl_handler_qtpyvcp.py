#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import os
#import linuxcnc
#import openpyxl

from qtpyvcp.widgets.form_widgets.main_window import VCPMainWindow
from qtpyvcp import hal

class BallScrewControlMainWindow(VCPMainWindow):
    """Main window class for the Mini example VCP."""
    def __init__(self, *args, **kwargs):
        super(BallScrewControlMainWindow, self).__init__(*args, **kwargs)

        #comp = hal.component('hello')
        #comp.addPin('testing', 'float', 'in')
        #comp.addListener('testing', self.onHalTestingChanged)
        #comp.ready()

    def onHalTestingChanged(self, val):
        print("hello.testing value changed: ", val)
        
    def onBtnNext(self):
        print "*** onBtnNext clicked"
        if(self.ui.cmbTestType.currentIndex()<4):
            self.ui.stackedWidget.setCurrentIndex(self.ui.cmbTestType.currentIndex()+1)
        else:
            self.ui.stackedWidget.setCurrentIndex(3)
        # self.close() только для случая многооконного интерфейса
