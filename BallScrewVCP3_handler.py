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

    ########################
    # CALLBACKS FROM STATUS#
    ########################

    #######################
    # CALLBACKS FROM FORM #
    #######################
    def init_pins(self):
        # создание HAL-пинов приложения
        self.VCP_halpins_float = {

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

    def onBtnLoadGCode(self):
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
        self.load_ini()
        self.init_led_colors()
        #self.w.lblTest = QHalLabel()
        #self.w.lblTest.setText("!!!HAL Label!!!")
        # self.w.gridLayout_29.addWidget(self.w.lblTest, 3, 2)
        self.init_plot()

    def init_led_colors(self):
        # настройка цветов диодов (т.к. в дизайнере цвета выставляются с ошибками - одинаковый цвет для color и off_color)
        diodes_redgreen = (

        self.w.ledEstop_Ext33,
        self.w.ledOn_Position33,
        self.w.ledAt_Load33,
        self.w.ledEnable33,
        self.w.ledEstop_Ext33,
        self.w.ledLoad_Is_On2_33,
        self.w.ledLoad_Alarm33,
        self.w.ledLoad_Error33,
        self.w.ledLoad_Overload33,
        self.w.ledLoad_Overheat33,
        self.w.lepPos_Is_On33,
        self.w.ledPos_Alarm33,
        self.w.ledPos_Error33,
        self.w.ledPos_Overload33,
        self.w.ledPos_Overheat33,
        self.w.ledPos_Sip33,
        self.w.ledLimits_Excess33)

        for led in diodes_redgreen:
            led.setColor(Qt.green)
            led.setOffColor(Qt.green)

        return

    def init_plot(self):
        self.w.plt33.showGrid(x = True, y = True)
        self.w.plt33.setBackground('w')
        styles = {'color':'r', 'font-size':'20px'}
        self.w.plt33.setLabel('left', 'T [Н*м]', **styles)
        self.w.plt33.setLabel('bottom', 'Время', **styles)

        font=QtGui.QFont()
        font.setPixelSize(20)
        self.hLine = pg.InfiniteLine(angle=0, movable=False,
            pen=pg.mkPen(color=QColor(Qt.blue),
            width = 2, style=Qt.DashDotLine),
            label='{value:0.1f}',
            labelOpts={'position':0.95, 'color': (255,0,0),
                       'movable': False, 'fill': (0, 0, 200, 100)})
        #self.hLine.setPos(pg.Point(0.0, 10.0))
        self.hLine.setValue(0.5)
        self.hLine.setZValue(1)
        self.w.plt33.addItem(self.hLine, ignoreBounds=True)

        self.vLine = pg.InfiniteLine(angle=90, movable=False,
            pen=pg.mkPen(color=QColor(Qt.blue), width = 2, style=Qt.DashDotLine))
        #self.vLine.setPos(pg.Point(1.0, 0.0))
        self.vLine.setValue(0.5)
        self.vLine.setZValue(1)
        self.w.plt33.addItem(self.vLine, ignoreBounds=True)

        font=QtGui.QFont()
        font.setPixelSize(20)
        #plot.getAxis("bottom").tickFont = font
        self.w.plt33.getAxis("bottom").setStyle(tickFont = font)
        self.w.plt33.getAxis("left").setStyle(tickFont = font)
        # self.graphWidget.setXRange(5, 20, padding=0)
        # self.graphWidget.setYRange(30, 40, padding=0)
        # курсор на графике https://stackoverflow.com/questions/50512391/can-i-share-the-crosshair-with-two-graph-in-pyqtgraph-pyqt5
        # https://stackoverflow.com/questions/52410731/drawing-and-displaying-objects-and-labels-over-the-axis-in-pyqtgraph-how-to-do
        return

    def pinCnagedCallback(self, data):
        halpin_name = self.w.sender().text()
        # отдельный пин, поставляющий float-параметр для построения графика
        if(halpin_name == 'position-pin31'):
            #print "*** update and plot"
            self.append_data(self.current_plot_n, self.hal['position-pin31']) # добавить точку к буферу графика
            self.update_plot() # обновить график
            return

        # отдельные пины, отвечающий за активность графических компонентов
        if(halpin_name == 'active_1-pin'):
            self.w.btnJog_Plus33.setEnabled(self.hal['active_1-pin'])
            self.w.btnJog_Minus33.setEnabled(self.hal['active_1-pin'])
            return

        # отдельные пины, отвечающий за активность графических компонентов
        if(halpin_name == 'active_2-pin'):
            self.w.chkDsp_Mode33.setEnabled(self.hal['active_2-pin'])
            #TODO на форме 33 два dsp_mode self.w.rbDsp_Mode33.setEnabled(self.hal['active_2-pin'])
            return

        # отдельные пины, отвечающий за активность графических компонентов
        if(halpin_name == 'active_3-pin'):
            self.w.sldDsp_Idle33.setEnabled(self.hal['active_3-pin'])
            self.w.sldVel_Idle33.setEnabled(self.hal['active_3-pin'])
            self.w.sldAccel_Idle33.setEnabled(self.hal['active_3-pin'])
            self.w.sldLoad33.setEnabled(self.hal['active_3-pin'])
            self.w.sldPos_Measure33.setEnabled(self.hal['active_3-pin'])
            self.w.sldDsp_Measure33.setEnabled(self.hal['active_3-pin'])
            self.w.sldVel_Measure33.setEnabled(self.hal['active_3-pin'])
            self.w.sldAccel_Measure33.setEnabled(self.hal['active_3-pin'])
            self.w.btnSaveGCode33.setEnabled(self.hal['active_3-pin'])

            return

        # отдельные пины, отвечающий за активность графических компонентов
        if(halpin_name == 'active_5-pin'):
            self.w.btnLoadGCode33.setEnabled(self.hal['active_5-pin'])
            self.w.btnProgram_Run33.setEnabled(self.hal['active_5-pin'])
            self.w.btnProgram_Stop33.setEnabled(self.hal['active_5-pin'])

            return

        # соответствие пинов float и табличек, на которых нужно отображать значение
        halpins_labels_match_precision2 = { # отображать с точностью 2 знака после запятой

            }

        if(halpin_name in halpins_labels_match_precision2):
            halpin_value = self.hal[halpin_name]
            halpins_labels_match_precision2[halpin_name].setText("{:10.2f}".format(halpin_value))

        halpins_labels_match_precision1 = { # отображать с точностью 1 знак после запятой

            # На форме 3.3
            'position':self.w.lblPosition33,
            'position_actual':self.w.lblPosition_Actual33,
            'load':self.w.lblLoad33,
            'load_actual':self.w.lblLoadActual33,

            # "таблица" с диодами и надписями на Форме 3.3
            'load_error_value':self.w.lblLoad_Error_Value33,
            'load_error_value_max':self.w.lblLoad_Error_Value_Max33,
            'load_overload_value':self.w.lblLoad_Overload_Value33,
            'load_overload_value_max':self.w.lblLoad_Overload_Value_Max33,
            'load_temperature':self.w.lblLoad_Temperature33,
            'load_temperature_max':self.w.lblLoad_Temperature_Max33,

            'pos_error_value':self.w.lblPos_Error_Value33,
            'pos_error_value_max':self.w.lblPos_Error_Value_max33,
            'pos_overload_value':self.w.lblPos_Overload_Value33,
            'pos_overload_value_max':self.w.lblPos_Overload_Value_max33,
            'pos_temperature':self.w.lblPos_Temperature33,
            'pos_temperature_max':self.w.lblPos_Temperature_Max33,
            'torque_extremal_last':self.w.lblTorque_Extremal_Last33,
            'torque_extremal_max':self.w.lblTorque_Extremal_Max33
        }

        if(halpin_name in halpins_labels_match_precision1):
            halpin_value = self.hal[halpin_name]
            halpins_labels_match_precision1[halpin_name].setText("{:10.1f}".format(halpin_value))

        return
        #print "Test pin value changed to:" % (data) # ВЫВОДИТ ВСЕГДА 0 - ВИДИМО ОШИБКА В ДОКУМЕНТАЦИИ
        #print 'halpin object =', self.w.sender()
        #print 'Halpin type: ',self.w.sender().get_type()

    def append_data(self, p_time, p_pos_measure, p_load, p_torque_at_load, p_torque_extremal):
        '''
        Функция для фиксирования новых показаний в массиве, по которому будет строиться график и записываться файл
        :param p_time:
        :param p_pos_measure:
        :param p_load:
        :param p_torque_at_load:
        :param p_torque_extremal:
        :return:
        '''
        # Вектор параметров состояния: (time; pos_measure; load; torque_at_load; torque_extremal)
        self.data['time'][self.current_plot_n] = p_time
        self.data['pos_measure'][self.current_plot_n] = p_pos_measure
        self.data['load'][self.current_plot_n] = p_load
        self.data['torque_at_load'][self.current_plot_n] = p_torque_at_load
        self.data['torque_extremal'][self.current_plot_n] = p_torque_extremal
        self.current_plot_n += 1
        # if(self.current_plot_n >= 10000):
        #     self.current_plot_n = 0 # логика кольцевого буфера
        return

    def update_plot(self):
        '''
        Функция для построения графика в координатах position(X)-torque(Y)
        :return:
        '''

        if(self.current_plot_n < 20):
            #print "*** plot < 20"
            self.w.plt33.plot(self.data[0][0:self.current_plot_n],
                              self.data[1][0:self.current_plot_n],
                              clear = True)
        else:
            #print "*** plot >= 20"
            self.w.plt33.plot(self.data[0][self.current_plot_n-20:self.current_plot_n],
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
    def load_ini(self):
        ini_control_match_dict = {
            'NOM_DSP_IDLE' : (self.w.sldDsp_Idle33, self.w.spnDsp_Idle33),
            'NOM_VEL_IDLE' : (self.w.sldVel_Idle33, self.w.spnVel_Idle33),
            'NOM_ACCEL_IDLE' : (self.w.sldAccel_Idle33, self.w.spnAccel_Idle33),
            'NOM_LOAD' : (self.w.sldLoad33, self.w.spnLoad33),
            'NOM_POS_MEASURE' : (self.w.sldPos_Measure33, self.w.spnPos_Measure33),
            'NOM_DSP_MEASURE' : (self.w.sldDsp_Measure33, self.w.spnDsp_Measure33),
            'NOM_VEL_MEASURE' : (self.w.sldVel_Measure33, self.w.spnVel_Measure33),
            'NOM_ACCEL_MEASURE' : (self.w.sldAccel_Measure33, self.w.spnAccel_Measure33),
        }

        for key, controls in ini_control_match_dict.items():
            print '***controls[0] = ', controls[0].objectName()
            print '***controls[1] = ', controls[1].objectName()
            controls[0].setMinimum(int(float(INFO.INI.findall("BALLSCREWPARAMS", key+'_MIN')[0])*100))
            controls[0].setMaximum(int(float(INFO.INI.findall("BALLSCREWPARAMS", key+'_MAX')[0])*100))
            controls[0].setValue(int(float(INFO.INI.findall("BALLSCREWPARAMS", key)[0])*100))
            controls[1].setMinimum(float(INFO.INI.findall("BALLSCREWPARAMS", key+'_MIN')[0]))
            controls[1].setMaximum(float(INFO.INI.findall("BALLSCREWPARAMS", key+'_MAX')[0]))
            controls[1].setValue(float(INFO.INI.findall("BALLSCREWPARAMS", key)[0]))
            #controls[0].valueChanged.connect(lambda val1: controls[1].setValue(float(val1)/100.0))
            #controls[1].valueChanged.connect(lambda val2: controls[0].setValue(int(val2*100)))

        self.w.sldDsp_Idle33.valueChanged.connect(lambda val: self.w.spnDsp_Idle33.setValue(float(val)/100.0))
        self.w.spnDsp_Idle33.valueChanged.connect(lambda val: self.w.sldDsp_Idle33.setValue(int(val*100)))

        self.w.sldVel_Idle33.valueChanged.connect(lambda val: self.w.spnVel_Idle33.setValue(float(val)/100.0))
        self.w.spnVel_Idle33.valueChanged.connect(lambda val: self.w.sldVel_Idle33.setValue(int(val*100)))

        self.w.sldAccel_Idle33.valueChanged.connect(lambda val: self.w.spnAccel_Idle33.setValue(float(val)/100.0))
        self.w.spnAccel_Idle33.valueChanged.connect(lambda val: self.w.sldAccel_Idle33.setValue(int(val*100)))

        self.w.sldLoad33.valueChanged.connect(lambda val: self.w.spnLoad33.setValue(float(val)/100.0))
        self.w.spnLoad33.valueChanged.connect(lambda val: self.w.sldLoad33.setValue(int(val*100)))

        self.w.sldPos_Measure33.valueChanged.connect(lambda val: self.w.spnPos_Measure33.setValue(float(val)/100.0))
        self.w.spnPos_Measure33.valueChanged.connect(lambda val: self.w.sldPos_Measure33.setValue(int(val*100)))

        self.w.sldDsp_Measure33.valueChanged.connect(lambda val: self.w.spnDsp_Measure33.setValue(float(val)/100.0))
        self.w.spnDsp_Measure33.valueChanged.connect(lambda val: self.w.sldDsp_Measure33.setValue(int(val*100)))

        self.w.sldVel_Measure33.valueChanged.connect(lambda val: self.w.spnVel_Measure33.setValue(float(val)/100.0))
        self.w.spnVel_Measure33.valueChanged.connect(lambda val: self.w.sldVel_Measure33.setValue(int(val*100)))

        self.w.sldAccel_Measure33.valueChanged.connect(lambda val: self.w.spnAccel_Measure33.setValue(float(val)/100.0))
        self.w.spnAccel_Measure33.valueChanged.connect(lambda val: self.w.sldAccel_Measure33.setValue(int(val*100)))


        self.TYPE = INFO.INI.findall("BALLSCREWPARAMS", "TYPE")[0]
        self.DATALOGFILENAME = INFO.INI.findall("BALLSCREWPARAMS", "LOGFILE")[0]
        self.MODEL = INFO.INI.findall("BALLSCREWPARAMS", "MODEL")[0]
        self.DATE = INFO.INI.findall("BALLSCREWPARAMS", "DATE")[0]
        self.PART = INFO.INI.findall("BALLSCREWPARAMS", "PART")[0]
        #self.datalog.write("Номер изделия: " + self.PART + "\n")
        #self.datalog.write("Дата: " + self.DATE + "\n")

        #TODO обработка ошибок и исключений: 1) нет файла - сообщение и заполнение по умолчанию, создание конфига
        #TODO обработка ошибок и исключений: 2) нет ключей в конфиге - сообщение и заполнение по умолчанию

    
################################
# required handler boiler code #
################################

def get_handlers(halcomp, widgets, paths):
     return [HandlerClass(halcomp, widgets, paths)]
