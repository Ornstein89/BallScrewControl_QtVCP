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
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import Qt
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
        self.w.ledPos_Alarm31.setOffColor(Qt.yellow)
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
        'position-pin31': None,
        'position_actual-pin31': None,
        'time_current-pin32': None,
        'duration-pin32':None,
        'torque_set-pin32': None,
        'torque_actual-pin32': None,
        'omega_actual-pin32': None,
        'geartorque_error_value-pin32': None,
        'geartorque_error_value_max32': None, # ограничение по длине имени пина 47 символов
        'brakeorque_error_value-pin32': None,
        'braketorque_error_value_max32': None, # ограничение по длине имени пина 47 символов
        'load_error_value-pin32': None,
        'load_error_value_max-pin32': None,
        'load_temperature-pin32': None,
        'load_temperature_max-pin32': None,
        'pos_temperature-pin32': None,
        'pos_temperature_max-pin32': None,
        'torque_actual-pin32': None,
        'torque_set-pin32': None,
        'torque_actual-pin32': None
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
        # настройка цветов диодов (т.к. в дизайнере цвета выставляются с ошибками - одинаковый цвет для color и off_color)
        diodes_redgreen = (

        self.w.ledPos_Alarm31,

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
        self.w.ledPos_Overheat32,

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
        self.w.ledLimits_Excess33,

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

        #TODO настройка осей графика
        self.TYPE = INFO.INI.findall("BALLSCREWPARAMS", "TYPE")[0]
        self.DATALOGFILENAME = INFO.INI.findall("BALLSCREWPARAMS", "LOGFILE")[0]
        self.w.stackedWidget.setCurrentIndex(int(self.TYPE)-1)
        self.load_ini(int(self.TYPE))
        self.w.plt32.showGrid(x = True, y = True)
        self.w.plt32.setBackground('w')
        pen = pg.mkPen(color=(255, 0, 0), width=2)
        self.w.plt32.setPen(pen)
        styles = {'color':'r', 'font-size':'20px'}
        self.w.plt32.setLabel('left', 'Момент [Н*м]', **styles)
        self.w.plt32.setLabel('bottom', 'Время', **styles)
        # self.graphWidget.setXRange(5, 20, padding=0)
        # self.graphWidget.setYRange(30, 40, padding=0)
        # курсор на графике https://stackoverflow.com/questions/50512391/can-i-share-the-crosshair-with-two-graph-in-pyqtgraph-pyqt5
        # https://stackoverflow.com/questions/52410731/drawing-and-displaying-objects-and-labels-over-the-axis-in-pyqtgraph-how-to-do
d
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
        if(halpin_name == 'active_0-pin'):
            self.w.sldVelocity31.setEnabled(self.hal['active_0-pin'])
            self.w.sldAcceleration31.setEnabled(self.hal['active_0-pin'])
            return

        # отдельные пины, отвечающий за активность графических компонентов
        if(halpin_name == 'active_1-pin'):
            self.w.btnJog_Plus33.setEnabled(self.hal['active_1-pin'])
            self.w.btnJog_Minus33.setEnabled(self.hal['active_1-pin'])
            self.w.btnJog_Plus34.setEnabled(self.hal['active_1-pin'])
            self.w.btnJog_Minus34.setEnabled(self.hal['active_1-pin'])
            return

        # отдельные пины, отвечающий за активность графических компонентов
        if(halpin_name == 'active_2-pin'):
            self.w.chkDsp_Mode33.setEnabled(self.hal['active_2-pin'])
            #TODO на форме 33 два dsp_mode self.w.rbDsp_Mode33.setEnabled(self.hal['active_2-pin'])
            self.w.chkDsp_Mode34.setEnabled(self.hal['active_2-pin'])
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

            self.w.sldDsp34.setEnabled(self.hal['active_3-pin'])
            self.w.sldOmg34.setEnabled(self.hal['active_3-pin'])
            self.w.sldAccel_Coeff34.setEnabled(self.hal['active_3-pin'])
            self.w.sldF1_34.setEnabled(self.hal['active_3-pin'])
            self.w.sldF2_34.setEnabled(self.hal['active_3-pin'])
            self.w.btnSaveGCode34.setEnabled(self.hal['active_3-pin'])

            return

        # отдельные пины, отвечающий за активность графических компонентов
        if(halpin_name == 'active_4-pin'):
            self.w.mdiline33.setEnabled(self.hal['active_4-pin'])
            self.w.btnLoadGCode34.setEnabled(self.hal['active_4-pin'])
            self.w.btnProgram_Run34.setEnabled(self.hal['active_4-pin'])
            self.w.btnProgram_Pause34.setEnabled(self.hal['active_4-pin'])
            self.w.btnProgram_Stop34.setEnabled(self.hal['active_4-pin'])
            return

        # отдельные пины, отвечающий за активность графических компонентов
        if(halpin_name == 'active_5-pin'):
            self.w.btnLoadGCode33.setEnabled(self.hal['active_5-pin'])
            self.w.btnProgram_Run33.setEnabled(self.hal['active_5-pin'])
            self.w.btnProgram_Stop33.setEnabled(self.hal['active_5-pin'])

            return

        # соответствие пинов float и табличек, на которых нужно отображать значение
        halpins_labels_match_precision2 = { # отображать с точностью 2 знака после запятой
            'position-pin31':self.w.lblPosition31,
            'position_actual-pin31':self.w.lblPosition_Actual31,
            }

        if(halpin_name in halpins_labels_match_precision2):
            halpin_value = self.hal[halpin_name]
            halpins_labels_match_precision2[halpin_name].setText("{:10.2f}".format(halpin_value))

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
            'pos_temperature_max-pin32':self.w.lblPos_Temperature_Max32,

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
            'torque_extremal_max':self.w.lblTorque_Extremal_Max33,

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
            self.w.plt32.plot(self.data[0][0:self.current_plot_n],
                              self.data[1][0:self.current_plot_n],
                              clear = True)
        else:
            #print "*** plot >= 20"
            self.w.plt32.plot(self.data[0][self.current_plot_n-20:self.current_plot_n],
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
        # для формы 3.1
        {
            'NOM_VEL' : self.w.sldVelocity31,
            'NOM_ACCEL' : self.w.sldAcceleration31
        },
        # для формы 3.2
        {},
        # для формы 3.3
        {
            'NOM_DSP_IDLE' : self.w.sldDsp_Idle33,
            'NOM_VEL_IDLE' : self.w.sldVel_Idle33,
            'NOM_ACCEL_IDLE' : self.w.sldAccel_Idle33,
            'NOM_DSP_MEASURE' : self.w.sldDsp_Measure33,
            'NOM_VEL_MEASURE' : self.w.sldVel_Measure33,
            'NOM_ACCEL_MEASURE' : self.w.sldAccel_Measure33,
            'NOM_LOAD' : self.w.sldLoad33,
            'NOM_POS_MEASURE' : self.w.sldPos_Measure33
        },
        # для формы 3.4
        {
            'NOM_TRAVEL' : self.w.sldDsp34,
            'NOM_OMEGA' : self.w.sldOmg34,
            'NOM_ACCEL_COEFF' : self.w.sldAccel_Coeff34,
            'NOM_F1' : self.w.sldF1_34,
            'NOM_F2' : self.w.sldF2_34
        }
        )

        #self.TYPE = INFO.INI.findall("BALLSCREWPARAMS", "TYPE")[0]
        #print "*** self.TYPE = ", self.TYPE
        self.MODEL = INFO.INI.findall("BALLSCREWPARAMS", "MODEL")[0]
        self.DATE = INFO.INI.findall("BALLSCREWPARAMS", "DATE")[0]
        self.PART = INFO.INI.findall("BALLSCREWPARAMS", "PART")[0]
        #self.datalog.write("Номер изделия: " + self.PART + "\n")
        #self.datalog.write("Дата: " + self.DATE + "\n")
        for key, sldr in ini_control_match_dict[int(self.TYPE)-1].items():
            sldr.setMinimum(float(INFO.INI.findall("BALLSCREWPARAMS", key+'_MIN')[0]))
            sldr.setMaximum(float(INFO.INI.findall("BALLSCREWPARAMS", key+'_MAX')[0]))
            sldr.setValue(float(INFO.INI.findall("BALLSCREWPARAMS", key)[0]))
        #TODO обработка ошибок и исключений: 1) нет файла - сообщение и заполнение по умолчанию, создание конфига
        #TODO обработка ошибок и исключений: 2) нет ключей в конфиге - сообщение и заполнение по умолчанию

    
################################
# required handler boiler code #
################################

def get_handlers(halcomp, widgets, paths):
     return [HandlerClass(halcomp, widgets, paths)]
