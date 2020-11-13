#!/usr/bin/python
# -*- coding: utf-8 -*-

# правила оформления кода в проекте
# 1) цифры в конце пинов и графических компонентов означают отношение к форме с заданным номером:
# 2) названия графических компонентов, которые соотосятся с пинами, образованы от названия пина
# 3) тип графического компонента указан в начале его названия (led, btn, chk и пр.)
# Пример: ledPos_Alarm31 - светодиод, который привязан к пину pos_alarm и находится на форме 3.1


############################
# **** IMPORT SECTION **** #
############################
# стандартные пакеты
import sys, os, configparser

# пакеты linuxcnc
import linuxcnc, hal # http://linuxcnc.org/docs/html/hal/halmodule.html

# пакеты GUI
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
#from qtvcp.widgets import FocusOverlay
from qtvcp.widgets.mdi_line import MDILine as MDI_WIDGET
from qtvcp.widgets.gcode_editor import GcodeEditor as GCODE
from qtvcp.lib.keybindings import Keylookup
from qtvcp.lib.gcodes import GCodes
from qtvcp.core import Status, Action, Info

# пакеты для графиков
import pyqtgraph as pg
from pyqtgraph import PlotWidget, plot

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
INFO = Info()
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
        self.PATHS = paths
        self.gcodes = GCodes()
        self.data = [[None for _ in range(10000)],[None for _ in range(10000)]]
        self.current_plot_n = 0
        self.w = widgets
        self.init_pins()

    ##########################################
    # SPECIAL FUNCTIONS SECTION              #
    ##########################################

    # at this point:
    # the widgets are instantiated.
    # the HAL pins are built but HAL is not set ready
    # This is where you make HAL pins or initialize state of widgets etc
    def initialized__(self):
        self.init_gui()
        self.start_log(self.DATALOGFILENAME)
        # self.gcodes.setup_list() инструкция нужна только для отображения справочного списка команд

        #fov = FocusOverlay(self)
        #fov.show()

    def processed_key_event__(self,receiver,event,is_pressed,key,code,shift,cntrl):
        if event.key() == Qt.Key_Left and self.w.btnJog_Minus34.isEnabled():
            if is_pressed and not self.w.btnJog_Minus34.isDown():
                self.w.btnJog_Minus34.setDown(True)
                #self.w.btnJog_Minus34.click(True)
                self.w.btnJog_Minus34.pressed.emit()
                #self.w.btnJog_Minus34.setCheckable(True)
                #self.w.btnJog_Minus34.setChecked(True)
            elif self.w.btnJog_Minus34.isDown():
                self.w.btnJog_Minus34.setDown(False)
                #self.w.btnJog_Minus34.click(False)
                self.w.btnJog_Minus34.released.emit()
                #self.w.btnJog_Minus34.setChecked(False)
                #self.w.btnJog_Minus34.setCheckable(False)
            #print '*** Qt.Key_Left'
            # event.accept()

        if event.key() == Qt.Key_Right and self.w.btnJog_Plus34.isEnabled():
            if is_pressed and not self.w.btnJog_Plus34.isDown():
                self.w.btnJog_Plus34.setDown(True)
                self.w.btnJog_Plus34.pressed.emit()
                # self.w.btnJog_Plus34.click(True)
                # self.w.btnJog_Plus34.press()
                # self.w.btnJog_Plus34.setCheckable(True)
                # self.w.btnJog_Plus34.setChecked(True)
            elif self.w.btnJog_Plus34.isDown():
                self.w.btnJog_Plus34.setDown(False)
                self.w.btnJog_Plus34.released.emit()
                # self.w.btnJog_Plus34.click(True)
                # self.w.btnJog_Plus34.release()
                # self.w.btnJog_Plus34.setChecked(False)
                # self.w.btnJog_Plus34.setCheckable(False)

            #print '*** Qt.Key_Right'
            # event.accept()

    ########################
    # CALLBACKS FROM STATUS#
    ########################

    #######################
    # CALLBACKS FROM FORM #
    #######################
    def init_pins(self):
        # создание HAL-пинов приложения
        self.VCP_halpins_float = {
        'position-pin31': None,
        }
        self.VCP_halpins_bit = {
        'active_0-pin':None,
        'active_1-pin':None,
        'active_2-pin':None,
        'active_3-pin':None,
        'active_4-pin':None,
        'active_5-pin':None
        }

        # создание пинов и связывание событий изменения HAL с обработчиком
        for key in self.VCP_halpins_float:
            self.VCP_halpins_float[key] = self.hal.newpin(key, hal.HAL_FLOAT, hal.HAL_IN)
            self.VCP_halpins_float[key].value_changed.connect(lambda s: self.pinCnagedCallback(s))
            # создание пинов и связывание событий изменения HAL с обработчиком
        for key in self.VCP_halpins_bit:
            self.VCP_halpins_bit[key] = self.hal.newpin(key, hal.HAL_BIT, hal.HAL_IN)
            self.VCP_halpins_bit[key].value_changed.connect(lambda s: self.pinCnagedCallback(s))
        return

    def onBtnLoadGCode34(self):
        # код на основе btn_load и load_code из qtdragon
        #fname = self.w.filemanager.getCurrentSelected()
        fname = QFileDialog.getOpenFileName(self.w, 'Open GCode file',
        ".","NGC (*.ngc);;Text files (*.txt);;All Files (*.*)")
        if fname[1] is None or fname[0] is None:
            #TODO уведомление
            return
        if fname[0].endswith(".ngc"):
            # self.w.cmb_gcode_history.addItem(fname) отобразить текущий файл в combobox
            # self.w.cmb_gcode_history.setCurrentIndex(self.w.cmb_gcode_history.count() - 1) отобразить текущий файл в combobox
            ACTION.OPEN_PROGRAM(fname[0])
            #self.add_status("Loaded program file : {}".format(fname))
            #self.w.main_tab_widget.setCurrentIndex(TAB_MAIN)
            STATUS.emit('update-machine-log', "Loaded program file : {}".format(fname), 'TIME')
            print "*** LOADED"
        else:
            self.add_status("Unknown or invalid filename")
            STATUS.emit('update-machine-log', "Unknown or invalid filename", 'TIME')
            print "*** ERROR LOAD FILE"

    def onBtnSaveGCode34(self):
        # загрузить шаблон
        # заполнить отмеченные места
        # диалог сохранения файла
        # сохранить файл
        pass

    def pnBtnShowResult34(self):
        #TODO открыть блокнот
        pass

    def onBtnClearPlot34(self):
        pass

    def onBtnShowForse34(self):
        pass

    def onBtnShowTorque34(self):
        pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Left:
            print '*** Qt.Key_Left'
            return
        if event.key() == Qt.Key_Right:
            print '*** Qt.Key_Right'
            return
        return

    #####################
    # GENERAL FUNCTIONS #
    #####################
    def init_gui(self):
        self.init_led_colors()
        #TODO настройка осей графика
        self.load_ini()
        self.init_plot()
        return

    def init_led_colors(self):
        # настройка цветов диодов (т.к. в дизайнере цвета выставляются с ошибками - одинаковый цвет для color и off_color)
        diodes_redgreen = (
        self.w.ledIs_Homed34,
        self.w.ledOn_Position34,
        self.w.ledAt_Load34,
        self.w.ledTorque_Error34,
        self.w.ledTorque1_Error34,
        self.w.ledEstop_Ext34,
        self.w.ledLoad_Is_On_2_34,
        self.w.ledLoad_Alarm34,
        self.w.ledLoad_Error34,
        self.w.ledLoad_Overload34,
        self.w.ledLoad_Overheat34,
        self.w.ledPos_Is_On_2_34,
        self.w.ledPoa_Alarm34,
        self.w.ledPos_Error34,
        self.w.ledPos_Overload34,
        self.w.ledPos_Overheat34,
        self.w.ledSlip34,
        self.w.ledLimits_Excess34)

        for led in diodes_redgreen:
            led.setColor(Qt.green)
            led.setOffColor(Qt.green)

    def init_plot(self):
        self.w.plt34.showGrid(x = True, y = True)
        self.w.plt34.setBackground('w')
        pen = pg.mkPen(color=(255, 0, 0), width=2)
        self.w.plt34.setPen(pen)
        styles = {'color':'r', 'font-size':'20px'}
        self.w.plt34.setLabel('left', 'Момент [Н*м]', **styles)
        self.w.plt34.setLabel('bottom', 'Время', **styles)
        # self.graphWidget.setXRange(5, 20, padding=0)
        # self.graphWidget.setYRange(30, 40, padding=0)
        # курсор на графике https://stackoverflow.com/questions/50512391/can-i-share-the-crosshair-with-two-graph-in-pyqtgraph-pyqt5
        # https://stackoverflow.com/questions/52410731/drawing-and-displaying-objects-and-labels-over-the-axis-in-pyqtgraph-how-to-do

    def pinCnagedCallback(self, data):
        halpin_name = self.w.sender().text()

        # отдельные пины, отвечающий за активность графических компонентов
        if(halpin_name == 'active_0-pin'):
            return

        # отдельные пины, отвечающий за активность графических компонентов
        if(halpin_name == 'active_1-pin'):
            self.w.btnJog_Plus34.setEnabled(self.hal['active_1-pin'])
            self.w.btnJog_Minus34.setEnabled(self.hal['active_1-pin'])
            return

        # отдельные пины, отвечающий за активность графических компонентов
        if(halpin_name == 'active_2-pin'):
            self.w.chkDsp_Mode34.setEnabled(self.hal['active_2-pin'])
            return

        # отдельные пины, отвечающий за активность графических компонентов
        if(halpin_name == 'active_3-pin'):
            self.w.sldDsp34.setEnabled(self.hal['active_3-pin'])
            self.w.sldOmg34.setEnabled(self.hal['active_3-pin'])
            self.w.sldAccel_Coeff34.setEnabled(self.hal['active_3-pin'])
            self.w.sldF1_34.setEnabled(self.hal['active_3-pin'])
            self.w.sldF2_34.setEnabled(self.hal['active_3-pin'])
            self.w.btnSaveGCode34.setEnabled(self.hal['active_3-pin'])

            return

        # отдельные пины, отвечающий за активность графических компонентов
        if(halpin_name == 'active_4-pin'):
            self.w.btnLoadGCode34.setEnabled(self.hal['active_4-pin'])
            self.w.btnProgram_Run34.setEnabled(self.hal['active_4-pin'])
            self.w.btnProgram_Pause34.setEnabled(self.hal['active_4-pin'])
            self.w.btnProgram_Stop34.setEnabled(self.hal['active_4-pin'])
            return

        # отдельные пины, отвечающий за активность графических компонентов
        if(halpin_name == 'active_5-pin'):
            pass

            return

        # соответствие пинов float и табличек, на которых нужно отображать значение
        halpins_labels_match_precision2 = { # отображать с точностью 2 знака после запятой
            'position-pin31':self.w.lblPosition31,
            }

        if(halpin_name in halpins_labels_match_precision2):
            halpin_value = self.hal[halpin_name]
            halpins_labels_match_precision2[halpin_name].setText("{:10.2f}".format(halpin_value))

        halpins_labels_match_precision1 = { # отображать с точностью 1 знак после запятой

            #TODO для формы 3.4
            'position':self.w.lblPosition34,
            'position_actual':self.w.lblPosition_Actual34,
            'load':self.w.lblLoad34,
            'load_actual':self.w.lblLoad_Actual34,

            # "таблица" с диодами и надписями на Форме 3.4
            'torque_error_value':self.w.lblTorque_Error_Value34,
            'torque_error_value_max':self.w.lblTorque_Error_Value_Max34,
            'torque1_error_value':self.w.lblTorque1_Error_Value34,
            'torque1_error_value_max':self.w.lblTorque1_Error_Value_Max34,
            'load_error_value':self.w.lblLoad_Error_Value34,
            'load_error_value_max':self.w.lblLoad_Error_Value_Max34,
            'load_overload_value':self.w.lblLoad_Overload_Value34,
            'load_overload_value_max':self.w.lblLoad_Overload_Value_Max34,
            'load_temperature':self.w.lblLoad_Temperature34,
            'load_temperature_max':self.w.lblLoad_Temperature_Max34,
            'pos_error_value':self.w.lblPos_Error_Value34,
            'pos_error_value_max':self.w.lblPos_Error_Value_Max34,
            'pos_overload_value':self.w.lblPos_Overload_Value34,
            'pos_overload_value_max':self.w.lblPos_Overload_Value_Max34,
            'pos_temperature':self.w.lblPos_Temperature34,
            'pos_temperature_max':self.w.lblPos_Temperature_Max34,
            'torque_max':self.w.lblTorque_Max34,
        }

        if(halpin_name in halpins_labels_match_precision1):
            halpin_value = self.hal[halpin_name]
            halpins_labels_match_precision1[halpin_name].setText("{:10.1f}".format(halpin_value))

        return
        #print "Test pin value changed to:" % (data) # ВЫВОДИТ ВСЕГДА 0 - ВИДИМО ОШИБКА В ДОКУМЕНТАЦИИ
        #print 'halpin object =', self.w.sender()
        #print 'Halpin type: ',self.w.sender().get_type()

    def append_data(self, x, y):
        self.data[0][self.current_plot_n] = x
        self.data[1][self.current_plot_n] = y
        self.current_plot_n += 1
        if(self.current_plot_n >= 10000):
            self.current_plot_n = 0 # логика кольцевого буфера
        return

    def update_plot(self):
        if(self.current_plot_n < 20):
            #print "*** plot < 20"
            self.w.plt34.plot(self.data[0][0:self.current_plot_n],
                              self.data[1][0:self.current_plot_n],
                              clear = True)
        else:
            #print "*** plot >= 20"
            self.w.plt34.plot(self.data[0][self.current_plot_n-20:self.current_plot_n],
                              self.data[1][self.current_plot_n-20:self.current_plot_n],
                              clear=True)
        return

    def flush_to_log(self):
        logfile = open('temp_log.log', 'w')
        #Заголовок лога
        logfile.write('Модель: ', self.MODEL, '\n')
        logfile.write('Номер изделия: ', self.PART, '\n')
        logfile.write('Дата: ', self.DATE, '\n')
        logfile.write('\n')
        for i in range(self.current_plot_n):
            logfile.write(self.data[0][i], self.data[1][i])
        logfile.close()
        return

    def on_siggen_test_read_pin_value_changed(self, data):
        return
        #print("*** siggen pin data: ", data)
        #print("*** siggen pin: ", self.siggen_test_read_pin.get())
        #print("*** siggen.0.sine directly", hal.get_value("siggen.0.sine"))

    def start_log(self, logfilename):
        self.datalog = None
        self.datalog = open(logfilename,"w")
        self.datalog.write("Модель: " + self.MODEL + "\n")
        self.datalog.write("Номер изделия: " + self.PART + "\n")
        self.datalog.write("Дата: " + self.DATE + "\n")

    #TODO в принципе функция не нужна, т.к. linuxcnc сам поддерживает передачу параметров из ini
    def load_ini(self, n_form):
        ini_control_match_dict = (
        # для формы 3.4
        {
            'NOM_DSP' : [self.w.sldDsp34, self.w.spnDsp34],
            'NOM_OMG': [self.w.sldOmg34, self.w.spnOmg34],
            'NOM_ACCEL_COEFF': [self.w.sldAccel_Coeff34, self.w.spnAccel_Coeff34],
            'NOM_F1': [self.w.sldF1_34, self.w.spnF1_34],
            'NOM_F2': [self.w.sldF2_34, self.w.spnF2_34]
        }
        )

        #self.TYPE = INFO.INI.findall("BALLSCREWPARAMS", "TYPE")[0]
        #print "*** self.TYPE = ", self.TYPE
        self.TYPE = INFO.INI.findall("BALLSCREWPARAMS", "TYPE")[0]
        self.DATALOGFILENAME = INFO.INI.findall("BALLSCREWPARAMS", "LOGFILE")[0]
        self.MODEL = INFO.INI.findall("BALLSCREWPARAMS", "MODEL")[0]
        self.DATE = INFO.INI.findall("BALLSCREWPARAMS", "DATE")[0]
        self.PART = INFO.INI.findall("BALLSCREWPARAMS", "PART")[0]
        #self.datalog.write("Номер изделия: " + self.PART + "\n")
        #self.datalog.write("Дата: " + self.DATE + "\n")
        for key, controls in ini_control_match_dict[int(self.TYPE)-1].items():
            controls[0].setMinimum(int(float(INFO.INI.findall("BALLSCREWPARAMS", key+'_MIN')[0])*100))
            controls[0].setMaximum(int(float(INFO.INI.findall("BALLSCREWPARAMS", key+'_MAX')[0])*100))
            controls[0].setValue(int(float(INFO.INI.findall("BALLSCREWPARAMS", key)[0])*100))
            controls[1].setMinimum(float(INFO.INI.findall("BALLSCREWPARAMS", key+'_MIN')[0]))
            controls[1].setMaximum(float(INFO.INI.findall("BALLSCREWPARAMS", key+'_MAX')[0]))
            controls[1].setValue(float(INFO.INI.findall("BALLSCREWPARAMS", key)[0]))

        self.w.sldDsp34.valueChanged.connect(lambda val: self.w.spnDsp34.setValue(float(val)/100.0))
        self.w.spnDsp34.valueChanged.connect(lambda val: self.w.sldDsp34.setValue(int(val*100)))

        self.w.sldOmg34.valueChanged.connect(lambda val: self.w.spnOmg34.setValue(float(val)/100.0))
        self.w.spnOmg34.valueChanged.connect(lambda val: self.w.sldOmg34.setValue(int(val*100)))

        self.w.sldAccel_Coeff34.valueChanged.connect(lambda val: self.w.spnAccel_Coeff34.setValue(float(val)/100.0))
        self.w.spnAccel_Coeff34.valueChanged.connect(lambda val: self.w.sldAccel_Coeff34.setValue(int(val*100)))

        self.w.sldF1_34.valueChanged.connect(lambda val: self.w.spnF1_34.setValue(float(val)/100.0))
        self.w.spnF1_34.valueChanged.connect(lambda val: self.w.sldF1_34.setValue(int(val*100)))

        self.w.sldF2_34.valueChanged.connect(lambda val: self.w.spnF2_34.setValue(float(val)/100.0))
        self.w.spnF2_34.valueChanged.connect(lambda val: self.w.sldF2_34.setValue(int(val*100)))

        #TODO обработка ошибок и исключений: 1) нет файла - сообщение и заполнение по умолчанию, создание конфига
        #TODO обработка ошибок и исключений: 2) нет ключей в конфиге - сообщение и заполнение по умолчанию

    
################################
# required handler boiler code #
################################

def get_handlers(halcomp, widgets, paths):
     return [HandlerClass(halcomp, widgets, paths)]
