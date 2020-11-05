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
        self.initialized = False
        self.hal = halcomp
        self.PATHS = paths
        self.gcodes = GCodes()
        self.plotdata = [[],[]]
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
        self.initialized = True
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
        'time_current-pin32': [None, self.onUpdateFloatSignals],
        'time-pin32': [None, self.onUpdateFloatSignals],
        'duration-pin32':[None, self.onUpdateFloatSignals],
        'torque_set-pin32': [None, self.onTorque_SetChanged], # пин связан с графиком, поэтому в отдельный слот для повышения производительности
        'torque_actual-pin32': [None, self.onTorque_ActualChanged], # пин связан с графиком, поэтому в отдельный слот для повышения производительности
        'omega_actual-pin32': [None, self.onUpdateFloatSignals],
        'geartorque_error_value-pin32': [None, self.onUpdateFloatSignals],
        'geartorque_error_value_max32': [None, self.onUpdateFloatSignals], # ограничение по длине имени пина 47 символов
        'brakeorque_error_value-pin32': [None, self.onUpdateFloatSignals],
        'braketorque_error_value_max32': [None, self.onUpdateFloatSignals], # ограничение по длине имени пина 47 символов
        'load_error_value-pin32': [None, self.onUpdateFloatSignals],
        'load_error_value_max-pin32': [None, self.onUpdateFloatSignals],
        'load_temperature-pin32': [None, self.onUpdateFloatSignals],
        'load_temperature_max-pin32': [None, self.onUpdateFloatSignals],
        'pos_temperature-pin32': [None, self.onUpdateFloatSignals],
        'pos_temperature_max-pin32': [None, self.onUpdateFloatSignals]
        }
        self.VCP_halpins_bit = {
        'dir-pin32':[None, self.onDirChanged],
        'append_buffer-pin32':[None, self.onAppend_BufferChanged],
        'append_file-pin32':[None,self.onAppend_FileChanged],
        'append_title-pin32':[None, self.onAppend_TitleChanged],
        }

        # создание пинов и связывание событий изменения HAL с обработчиком
        for key in self.VCP_halpins_float:
            tmp_pin = self.hal.newpin(key, hal.HAL_FLOAT, hal.HAL_IN)
            self.VCP_halpins_float[key][0] = tmp_pin
            tmp_pin.value_changed.connect(self.VCP_halpins_float[key][1])

            # создание пинов и связывание событий изменения HAL с обработчиком
        for key in self.VCP_halpins_bit:
            tmp_pin = self.hal.newpin(key, hal.HAL_BIT, hal.HAL_IN)
            self.VCP_halpins_bit[key][0] = tmp_pin
            tmp_pin.value_changed.connect(self.VCP_halpins_bit[key][1])
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

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Left:
            print '*** Qt.Key_Left'
            return
        if event.key() == Qt.Key_Right:
            print '*** Qt.Key_Right'
            return
        return

    def onTorque_SetChanged(self, data):
        if not self.initialized:
            return

        torque_set_value = self.hal['torque_set-pin32'] * 0.1 + 1.0
        #self.hLine.setPos(pg.Point(torque_set_value, 0.0))
        self.hLine.setValue(torque_set_value)
        return

    def onTorque_ActualChanged(self, data):
        if not self.initialized:
            return

        torque_actual_value = self.hal['torque_actual-pin32'] * 0.1 + 1.0
        time_value = self.hal['time-pin32']
        time_range = 15.0 #TODO заменить на сторонний сигнал

        # добавить точку
        self.plotdata[0].append(time_value)
        self.plotdata[1].append(torque_actual_value)

        # оставить только точки в пределах [time_value-timerange, time_value]
        plotindex = 0
        while self.plotdata[0][plotindex] < time_value - time_range:
            plotindex += 1
        self.plotdata[0] = self.plotdata[0][plotindex:]
        self.plotdata[1] = self.plotdata[1][plotindex:]
        YMax = 1.2#max(self.plotdata[1]) * 1.1
        # обновить график
        #self.vLine.setPos(pg.Point(0.0, time_value))
        self.w.plt32.setXRange(time_value - time_range, time_value + time_range*0.1)
        self.w.plt32.setYRange(0.0, YMax)
        #self.w.plt32.plot.clear()
        self.w.plt32.plot(self.plotdata[0][:],
                          self.plotdata[1][:],
        #                  clear = True,
                          pen = pg.mkPen(color=QColor(Qt.darkCyan), width=2))
        self.vLine.setValue(time_value)
        return

    def onUpdateFloatSignals(self, data):
        return

    def onTimeChanged(self, data):
        #TODO
        if not self.initialized:
            return

        self.current_time = self.hal['time-pin32']
        pass

    def onAppend_BufferChanged(self, data):
        # запись показаний производится в буфер для повышения производительности
        #TODO улучшить менеджмент памяти - выделять блоками (либо за этим следит интерпретатор питона)
        #TODO ограничение на длину???
        # Вектор параметров состояния: (time_current; torque_actual; omega_actual)
        # self.position_buffer.append([self.current_time, self.current_position]) # значения без лишнего обращения к пинам, для улучшения производительности
        if not self.initialized:
            return

        if not self.hal['append_buffer-pin32']:
            return

        self.position_buffer.append([self.hal['time_current-pin32'],
        self.hal['torque_actual-pin31'],
        self.hal['omega_actual']]) # получение значений с hal-пинов, может снижать производительность

        # форма 3.3, Вектор параметров состояния: (time; pos_measure; load; torque_at_load; torque_extremal)
        # self.position_buffer.append([time, pos_measure, load, torque_at_load, torque_extremal])
        # форма 3.4
        pass

    def onAppend_TitleChanged(self, data):
        if not self.hal['append_title-pin32']:
            return
        if not self.initialized:
            return
        self.logfile.write('Время запуска:\t' + str(time))
        self.logfile.write('Направление:\t' + str(dir))
        self.logfile.write('\n')
        self.logfile.write('Время работы\tКрутящий момент\tСкорость вращения')
        return

    def onAppend_FileChanged(self, data):
        #записать показания в файл
        if not self.hal['append_file-pin32']:
            return
        if not self.initialized:
            return
        for rec in self.position_buffer:
            str_to_print = ''
            for item in rec:
                str_to_print += str(item) + '\t'
            self.logfile.write(str_to_print)
        return

    def onDirChanged(self, data):
        pass

    #####################
    # GENERAL FUNCTIONS #
    #####################
    def init_gui(self):
        # настройка цветов диодов (т.к. в дизайнере цвета выставляются с ошибками - одинаковый цвет для color и off_color)
        diodes_redgreen = (
        self.w.ledIs_Running_Ccw32,
        self.w.ledIs_Running_Cw32,
        self.w.ledGeartorque_Error32,#.setOffColor(Qt.red)
        self.w.ledGeartorque_Error32,#.setColor(Qt.green)
        self.w.ledBraketorque_Error32,
        self.w.ledEstop_Ext32,
        self.w.ledLoad_Is_On2_32,
        self.w.ledLoad_Alarm32,
        self.w.ledLoad_Error32,
        self.w.ledLoad_Overheat32,
        self.w.ledPos_Is_On_2_32,
        self.w.ledPos_Alarm32,
        self.w.ledPos_Overheat32)

        for led in diodes_redgreen:
            led.setColor(Qt.green)
            led.setOffColor(Qt.green)

        #TODO настройка осей графика
        self.TYPE = INFO.INI.findall("BALLSCREWPARAMS", "TYPE")[0]
        self.DATALOGFILENAME = INFO.INI.findall("BALLSCREWPARAMS", "LOGFILE")[0]
        self.w.stackedWidget.setCurrentIndex(int(self.TYPE)-1)
        self.load_ini(int(self.TYPE))
        self.w.plt32.showGrid(x = True, y = True)
        self.w.plt32.setBackground('w')
        styles = {'color':'r', 'font-size':'20px'}
        self.w.plt32.setLabel('left', 'T [Н*м]', **styles)
        self.w.plt32.setLabel('bottom', 'Время', **styles)

        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen(color=QColor(Qt.blue), width = 2, style=Qt.DashDotLine))
        #self.hLine.setPos(pg.Point(0.0, 10.0))
        self.hLine.setValue(0.5)
        self.hLine.setZValue(1)
        self.w.plt32.addItem(self.hLine, ignoreBounds=True)

        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(color=QColor(Qt.blue), width = 2, style=Qt.DashDotLine))
        #self.vLine.setPos(pg.Point(1.0, 0.0))
        self.vLine.setValue(0.5)
        self.vLine.setZValue(1)
        self.w.plt32.addItem(self.vLine, ignoreBounds=True)

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

        halpins_labels_match_precision1 = { # отображать с точностью 1 знак после запятой
            # На форме 3.2
            'torque_set-pin32':self.w.lblTorque_Set32,
            'torque_actual-pin32':self.w.lblTorque_Actual32,
            'omega_actual-pin32':self.w.lblOmega_Actual32,

            # "таблица" с диодами и надписями на Форме 3.2
            'geartorque_error_value-pin32':self.w.lblGeartorque_Error_Value32,
            'geartorque_error_value_max32':self.w.lblGeartorque_Error_Value_Max32,
            'brakeorque_error_value-pin32':self.w.lblBraketorque_Error_Value32,
            'braketorque_error_value_max32':self.w.lblBraketorque_Error_Value_Max32,
            'load_error_value-pin32':self.w.lblLoad_Error_Value32,
            'load_error_value_max-pin32':self.w.lblLoad_Error_Value_Max32,
            'load_temperature-pin32':self.w.lblLoad_Temperature32,
            'load_temperature_max-pin32':self.w.lblLoad_Temperature_Max32,
            'pos_temperature-pin32':self.w.lblPos_Temperature32,
            'pos_temperature_max-pin32':self.w.lblPos_Temperature_Max32
        }

        if(halpin_name in halpins_labels_match_precision1):
            halpin_value = self.hal[halpin_name]
            halpins_labels_match_precision1[halpin_name].setText("{:10.1f}".format(halpin_value))

        return
        #print "Test pin value changed to:" % (data) # ВЫВОДИТ ВСЕГДА 0 - ВИДИМО ОШИБКА В ДОКУМЕНТАЦИИ
        #print 'halpin object =', self.w.sender()
        #print 'Halpin type: ',self.w.sender().get_type()

    def append_plot(self, x, y):
        self.plotdata[0][self.current_plot_n] = x
        self.plotdata[1][self.current_plot_n] = y
        self.current_plot_n += 1
        if(self.current_plot_n >= 10000):
            self.current_plot_n = 0 # логика кольцевого буфера
        return

    def update_plot(self):
        if(self.current_plot_n < 20):
            #print "*** plot < 20"
            self.w.plt32.plot(self.plotdata[0][0:self.current_plot_n],
                              self.plotdata[1][0:self.current_plot_n],
                              clear = True)
        else:
            #print "*** plot >= 20"
            self.w.plt32.plot(self.plotdata[0][self.current_plot_n-20:self.current_plot_n],
                              self.plotdata[1][self.current_plot_n-20:self.current_plot_n],
                              clear=True)
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
        #self.TYPE = INFO.INI.findall("BALLSCREWPARAMS", "TYPE")[0]
        #print "*** self.TYPE = ", self.TYPE
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
