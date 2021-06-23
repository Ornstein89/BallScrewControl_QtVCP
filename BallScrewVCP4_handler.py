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
import sys, os, io, re, configparser, subprocess
from datetime import datetime
import numpy as np
from scipy.linalg import *

# пакеты linuxcnc
import linuxcnc, hal # http://linuxcnc.org/docs/html/hal/halmodule.html

# пакеты GUI
from PyQt5 import QtCore, QtWidgets, QtGui, Qt
from PyQt5.QtWidgets import QFileDialog, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPixmap, QIcon

#from qtvcp.widgets import FocusOverlay
from qtvcp.widgets.mdi_line import MDILine as MDI_WIDGET
from qtvcp.widgets.gcode_editor import GcodeEditor as GCODE
from qtvcp.widgets.dialog_widget import LcncDialog
from qtvcp.widgets.overlay_widget import FocusOverlay

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
MSG = LcncDialog()

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
        self.RODOS_PATH = "/home/mdrives/RODOS4/RODOS4"
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
        self.init_datalog(self.DATALOGFILENAME)
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


    def closeEvent(self, event):
        self.w.overlay.text='Выключить?'
#        self.w.overlay.bg_color = QtGui.QColor(0, 0, 0,150)
        self.w.overlay.resize(self.w.size())
        self.w.overlay.show()
        self.w.overlay.update()

        answer = MSG.showdialog('Do you want to shutdown now?',
            details='You can set a preference to not see this message',
            display_type='YESNO')
        if not answer:
            self.w.overlay.hide()
            event.ignore()
            return

        self.update_ini()
        if self.datalogfile is not None:
            if not self.datalogfile.closed:
                self.datalogfile.flush()
                self.datalogfile.close()
        event.accept()
        print '*** closeEvent'
        return

    ########################
    # CALLBACKS FROM STATUS#
    ########################

    #######################
    # CALLBACKS FROM FORM #
    #######################
    def init_pins(self):
        # создание HAL-пинов приложения
        self.VCP_halpins_float = {
            'position-pin34':None,
            'position_actual-pin34':None,
            'load-pin34':None,
            'load_actual-pin34':None,
            'torque_actual-pin34':None,
            'torque-pin34':None,

            'torque_error_value-pin34':None,
            'torque_error_value_max-pin34':None,
            'torque1_error_value-pin34':None,
            'torque1_error_value_max-pin34':None,
            'load_error_value-pin34':None,
            'load_error_value_max-pin34':None,
            'load_overload_value-pin34':None,
            'load_overload_value_max-pin34':None,
            'load_temperature-pin34':None,
            'load_temperature_max-pin34':None,
            'pos_error_value-pin34':None,
            'pos_error_value_max-pin34':None,
            'pos_overload_value-pin34':None,
            'pos_overload_value_max-pin34':None,
            'pos_temperature-pin34':None,
            'pos_temperature_max-pin34':None,

            'torque_max-pin34':None,
            'f1-pin34':None,
            'f2-pin34':None,
            'dsp-pin34':None,
            'omega_actual-pin34':None

        }

        self.VCP_halpins_int = {
            'i-pin34':None,
            'N-pin34':None
        }

        for key in self.VCP_halpins_int:
            tmp_newpin = self.hal.newpin(key, hal.HAL_U32, hal.HAL_IN)
            self.VCP_halpins_int[key] = tmp_newpin
            self.VCP_halpins_int[key].value_changed.connect(lambda s: self.pinCnagedCallback(s))

        self.VCP_halpins_bit = {
            'append_title-pin34':[None,None], # соединение со слотом после открытия файла
            'append_buffer-pin34':[None,None], # соединение со слотом после открытия файла
            'append_file-pin34':[None,None], # соединение со слотом после открытия файла
            'log_permit-pin34':[None,None],

            'active_0-pin34':[None,self.guiStatesSwitch],
            'active_1-pin34':[None,self.guiStatesSwitch],
            'active_2-pin34':[None,self.guiStatesSwitch],
            'active_3-pin34':[None,self.guiStatesSwitch],
            'active_4-pin34':[None,self.guiStatesSwitch],

            'RODOS4_1_on': [None, lambda s: self.onRODOS_changed(s, 'RODOS4_1_on', 1, True)],
            'RODOS4_2_on': [None, lambda s: self.onRODOS_changed(s, 'RODOS4_2_on', 2, True)],
            'RODOS4_3_on': [None, lambda s: self.onRODOS_changed(s, 'RODOS4_3_on', 3, True)],
            'RODOS4_4_on': [None, lambda s: self.onRODOS_changed(s, 'RODOS4_4_on', 4, True)],
            'RODOS4_5_on': [None, lambda s: self.onRODOS_changed(s, 'RODOS4_5_on', 5, True)],
            'RODOS4_6_on': [None, lambda s: self.onRODOS_changed(s, 'RODOS4_6_on', 6, True)],

            'RODOS4_1_off': [None, lambda s: self.onRODOS_changed(s, 'RODOS4_1_off', 1, False)],
            'RODOS4_2_off': [None, lambda s: self.onRODOS_changed(s, 'RODOS4_2_off', 2, False)],
            'RODOS4_3_off': [None, lambda s: self.onRODOS_changed(s, 'RODOS4_3_off', 3, False)],
            'RODOS4_4_off': [None, lambda s: self.onRODOS_changed(s, 'RODOS4_4_off', 4, False)],
            'RODOS4_5_off': [None, lambda s: self.onRODOS_changed(s, 'RODOS4_5_off', 5, False)],
            'RODOS4_6_off': [None, lambda s: self.onRODOS_changed(s, 'RODOS4_6_off', 6, False)]
        }

        # создание пинов и связывание событий изменения HAL с обработчиком
        for key in self.VCP_halpins_float:
            self.VCP_halpins_float[key] = self.hal.newpin(key, hal.HAL_FLOAT, hal.HAL_IN)
            self.VCP_halpins_float[key].value_changed.connect(lambda s: self.pinCnagedCallback(s))

        # создание пинов и связывание событий изменения HAL с обработчиком
        for key in self.VCP_halpins_bit:
            tmp_newpin = self.hal.newpin(key, hal.HAL_BIT, hal.HAL_IN)
            self.VCP_halpins_bit[key][0] = tmp_newpin
            if self.VCP_halpins_bit[key][1] is not None:
                tmp_newpin.value_changed.connect(self.VCP_halpins_bit[key][1])

        # создание пинов и связывание событий для модели нагрузки, аппроксиматора и сборщика ошибок
        for i in range(100):
            pinname='err_pos_%d' % i 
            self.hal.newpin(pinname, hal.HAL_FLOAT, hal.HAL_IN)
            pinname='err_neg_%d' % i 
            self.hal.newpin(pinname, hal.HAL_FLOAT, hal.HAL_IN)
        
        for i in range(1,4):
            pinname='kpos%d' % i
            self.hal.newpin(pinname, hal.HAL_FLOAT, hal.HAL_OUT)
            pinname='kneg%d' % i
            self.hal.newpin(pinname, hal.HAL_FLOAT, hal.HAL_OUT)

        self.hal.newpin('position_terminal-pin34', hal.HAL_FLOAT, hal.HAL_OUT)
        self.hal['position_terminal-pin34'] = 50.0

        self.hal.newpin('n_of_points-pin34', hal.HAL_U32, hal.HAL_OUT)
        self.hal['n_of_points-pin34'] = 15

        return
    
    def onBtnBack(self):
        self.w.stackedWidget.setCurrentIndex(0)
        return
    
    def onBtnLoadApprox(self):
        self.w.stackedWidget.setCurrentIndex(1)
        return

    def onBtnLoadGCode34(self):
        # код на основе btn_load и load_code из qtdragon
        #fname = self.w.filemanager.getCurrentSelected()
        fname = QFileDialog.getOpenFileName(self.w, 'Open GCode file',
        ".","NGC (*.ngc);;Text files (*.txt);;All Files (*.*)")
        if fname[1] is None or fname[0] is None:
            #TODO уведомление
            return
        elif fname[0].endswith(".ngc"):
            # self.w.cmb_gcode_history.addItem(fname) отобразить текущий файл в combobox
            # self.w.cmb_gcode_history.setCurrentIndex(self.w.cmb_gcode_history.count() - 1) отобразить текущий файл в combobox
            ACTION.OPEN_PROGRAM(fname[0])
            #self.add_status("Loaded program file : {}".format(fname))            #self.w.main_tab_widget.setCurrentIndex(TAB_MAIN)
            #STATUS.emit('update-machine-log', "Loaded program file : {}".format(fname), 'TIME')
            #print "*** LOADED"
        else:
            #self.add_status("Unknown or invalid filename")
            #STATUS.emit('update-machine-log', "Unknown or invalid filename", 'TIME')
            #print "*** ERROR LOAD FILE"
            pass

    def onBtnSaveGCode34(self):
        replacements = [['{{dsp}}', '{:.1f}'.format(self.w.spnDsp34.value())],
            ['{{omg}}', '{:.1f}'.format(self.w.spnOmg34.value())],
            ['{{accel_coeff}}', '{:.1f}'.format(self.w.spnAccel_Coeff34.value())],
            ['{{f1}}', '{:.1f}'.format(self.w.spnF1_34.value())],
            ['{{f2}}', '{:.1f}'.format(self.w.spnF2_34.value())]]

        # открыть шаблон
        try:
            #f_template = open('BallScrewVCP3_template.ngc','rb')
            f_template = codecs.open('BallScrewVCP3_template.ngc','rb', 'utf-8')
            filedata = f_template.read()
            f_template.close()
        except:
            QMessageBox.critical(self.w, 'Ошибка',
            "Невозможно найти шаблон BallScrewVCP3_template.ngc", QMessageBox.Yes)
            return

        # заменить отмеченные места
        for replacement in replacements:
            filedata = filedata.replace(replacement[0], replacement[1])

        # записать файл
        fname = QFileDialog.getSaveFileName(self.w, 'Сохранить программу GCode',
        ".","NGC (*.ngc);;Text files (*.txt);;All Files (*.*)")

        if (not fname[0].endswith(".ngc")) or (fname[1] is None):
            # self.w.cmb_gcode_history.addItem(fname) отобразить текущий файл в combobox
            # self.w.cmb_gcode_history.setCurrentIndex(self.w.cmb_gcode_history.count() - 1) отобразить текущий файл в combobox
            #ACTION.OPEN_PROGRAM(fname[0])
            #self.add_status("Loaded program file : {}".format(fname))
            #self.w.main_tab_widget.setCurrentIndex(TAB_MAIN)
            #STATUS.emit('update-machine-log', "Loaded program file : {}".format(fname), 'TIME')
            QMessageBox.warning(self.w, 'Внимание',
            "Не выбрано название файла *.ngc для сохранения программы GCode", QMessageBox.Yes)
            return
            #self.add_status("Unknown or invalid filename")
            #STATUS.emit('update-machine-log', "Unknown or invalid filename", 'TIME')

        try:
            #f_final = open(fname[0], 'wb')
            f_final = codecs.open(fname[0], 'wb', 'utf-8')
            f_final.write(filedata)
            f_final.close()
        except:
            QMessageBox.critical(self.w, 'Ошибка',
            "Невозможно записать файл " + fname[0], QMessageBox.Yes)
            return
        pass


    def onBtnShowResult34(self):
        subprocess.Popen(['geany', self.DATALOGFILENAME])
        return


    #####################
    # GENERAL FUNCTIONS #
    #####################
    def guiStatesSwitch(self):
        self.w.btnHome34.setEnabled(self.hal['active_0-pin34'] and STATUS.machine_is_on())

        controls_on_active1 = [ # список элементов, которые становятся активны
            self.w.btnJog_Plus34,
            self.w.btnJog_Minus34]
        for control in controls_on_active1:
            control.setEnabled(self.hal['active_1-pin34'] and STATUS.machine_is_on())

        self.w.chkDsp_ModeOn34.setEnabled(self.hal['active_2-pin34'] and STATUS.machine_is_on())
        self.w.chkDsp_ModeOff34.setEnabled(self.hal['active_2-pin34'] and STATUS.machine_is_on())

        controls_on_active3 = [ # список элементов, которые становятся активны
            self.w.sldDsp34,
            self.w.spnDsp34,

            self.w.sldOmg34,
            self.w.spnOmg34,

            self.w.sldAccel_Coeff34,
            self.w.spnAccel_Coeff34,

            self.w.sldF1_34,
            self.w.spnF1_34,

            self.w.sldF2_34,
            self.w.spnF2_34,

            self.w.btnSaveGCode34]

        for control in controls_on_active3:
            control.setEnabled(self.hal['active_3-pin34'] and STATUS.machine_is_on())

        controls_on_active4 = [
            self.w.gcode_editor34, self.w.btnLoadGCode34,
            self.w.btnProgram_Run34, self.w.btnProgram_Pause34,
            self.w.btnProgram_Stop34]
        for control in controls_on_active4:
            control.setEnabled(self.hal['active_4-pin34'] and STATUS.machine_is_on())

        return

    def init_gui(self):
        self.w.setWindowIcon(QIcon("BallScrewControlIcon.png"))
        self.load_ini()
        self.init_led_colors()
        self.init_plot()

        STATUS.connect('state-estop',
                        lambda w: (self.w.btnDevice_On34.setEnabled(False),
                                   self.guiStatesSwitch()))
        STATUS.connect('state-estop-reset',
                        lambda w: (self.w.btnDevice_On34.setEnabled(not STATUS.machine_is_on()),
                                    self.guiStatesSwitch()))

        STATUS.connect('state-on', lambda _: (self.w.btnDevice_On34.setEnabled(False),
                                              self.guiStatesSwitch()))

        STATUS.connect('state-off', lambda _:(self.w.btnDevice_On34.setEnabled(STATUS.estop_is_clear()),
                                              self.guiStatesSwitch()))

        self.w.btnDevice_On34.clicked.connect(lambda x: ACTION.SET_MACHINE_STATE(True))
        self.w.btnDevice_Off34.clicked.connect(lambda x: ACTION.SET_MACHINE_STATE(False))

        # масштабирование выходных пинов слайдеров с помощью пинов *-scale
        # (команды setp в hal-файле недостаточно - слайдер не масштабирует,
        # пока не сдвинуть вручную)
        sliders_to_scale = [
            self.w.sldDsp34, self.w.sldOmg34, self.w.sldAccel_Coeff34,
            self.w.sldF1_34, self.w.sldF2_34]

        for slider_i in sliders_to_scale:
            slider_i.hal_pin_scale.set(0.01)
            slider_i.hal_pin_f.set(slider_i.value()*0.01)

        self.w.sldTestLoad.setValue(0.0)
        self.w.sldTestLoad.hal_pin_scale.set(0.1)
        self.w.sldTestLoad.hal_pin_f.set(0.0*0.01)

        # соединение слайдеров с переключателями
        self.w.sldDsp34.valueChanged.connect(lambda val: (self.w.spnDsp34.setValue(float(val)/100.0),
                                                          #self.w.plt34.setXRange(0, float(val)/100.0)
                                                          ))
        self.w.spnDsp34.valueChanged.connect(lambda val: (self.w.sldDsp34.setValue(int(val*100)),
                                                          #self.w.plt34.setXRange(0, val*100)
                                                          ))

        self.w.sldOmg34.valueChanged.connect(lambda val: self.w.spnOmg34.setValue(float(val)/100.0))
        self.w.spnOmg34.valueChanged.connect(lambda val: self.w.sldOmg34.setValue(int(val*100)))

        self.w.sldAccel_Coeff34.valueChanged.connect(lambda val: self.w.spnAccel_Coeff34.setValue(float(val)/100.0))
        self.w.spnAccel_Coeff34.valueChanged.connect(lambda val: self.w.sldAccel_Coeff34.setValue(int(val*100)))

        self.w.sldF1_34.valueChanged.connect(lambda val: (
                                        self.w.spnF1_34.setValue(float(val)/100.0),
                                        #self.w.plt34.setYRange(0.0, max(float(val)/100.0, self.w.spnF2_34.value())*1.2)
                                        ))
        self.w.spnF1_34.valueChanged.connect(lambda val: (
                                        self.w.sldF1_34.setValue(int(val*100)),
                                        #self.w.plt34.setYRange(0.0, max(val*100, self.w.spnF2_34.value())*1.2)
                                        ))

        self.w.sldF2_34.valueChanged.connect(lambda val: (
                                        self.w.spnF2_34.setValue(float(val)/100.0),
                                        #self.w.plt34.setYRange(0.0, max(float(val)/100.0, self.w.spnF1_34.value())*1.2)
                                        ))
        self.w.spnF2_34.valueChanged.connect(lambda val: (
                                        self.w.sldF2_34.setValue(int(val*100)),
                                        #self.w.plt34.setYRange(0.0, max(val*100, self.w.spnF1_34.value())*1.2)
                                        ))

        # экран-заглушка для графика пока не получены данные с устройства
        # self.w.plot_overlay = QLabel(self.w.plt34)
        # self.stub_image = QPixmap("stub_screen.png")
        # self.w.plot_overlay.setPixmap(self.stub_image)

        # приведение GUI в соответствие с сигналами HAL

        self.guiStatesSwitch()

        #self.w.wgtTestPanel.hide() # убрать панель с тестовым функционалом

        # оверлей для затенения окна
        self.w.overlay = FocusOverlay(self.w)
        self.w.overlay.setGeometry(0, 0, self.w.width(), self.w.height())
        self.w.overlay.hide()
        return

    def init_led_colors(self):
        # настройка цветов диодов (т.к. в дизайнере цвета выставляются с ошибками - одинаковый цвет для color и off_color)
        diodes_redgreen = (
            self.w.ledEnable34,
            self.w.ledIs_Homed34,
            self.w.ledOn_Position34,
            self.w.ledAt_Load34,
            # убрали из ТЗ 2 апреля self.w.ledTorque_Error34,
            # убрали из ТЗ 2 апреля self.w.ledTorque1_Error34,
            self.w.ledEstop_Ext34,
            # убрали из ТЗ 2 апреля self.w.ledLoad_Is_On_2_34,
            self.w.ledLoad_Alarm34,
            self.w.ledLoad_Error34,
            # убрали из ТЗ 2 апреля self.w.ledLoad_Overload34,
            self.w.ledLoad_Overheat34,
            # убрали из ТЗ 2 апреля self.w.ledPos_Is_On_2_34,
            self.w.ledPos_Alarm34,
            self.w.ledPos_Error34,
            # убрали из ТЗ 2 апреля self.w.ledPos_Overload34,
            self.w.ledPos_Overheat34,
            self.w.ledSlip34,
            self.w.ledLimits_Excess34)

        for led in diodes_redgreen:
            led.setColor(Qt.red)
            led.setOffColor(Qt.green)

        return

    def init_plot(self):
        self.w.plt34.showGrid(x = True, y = True)
        self.w.plt34.setBackground('w')
        styles = {'color':'r', 'font-size':'20px'}

        self.w.plt34.setLabel('left', 'F [кгс]', **styles)
        self.w.plt34.setLabel('bottom', 'Положение, мм', **styles)

        # дефолтное положение
        self.w.plt34.setYRange(0.0, 10)
        self.w.plt34.setXRange(0.0, 200)

        # размер шрифта числовых значений осей
        font=QtGui.QFont()
        font.setPixelSize(20)
        #plot.getAxis("bottom").tickFont = font
        self.w.plt34.getAxis("bottom").setStyle(tickFont = font)
        self.w.plt34.getAxis("left").setStyle(tickFont = font)

        # горизонтальная штриховая линия load/load_actual
        self.hLine = pg.InfiniteLine(angle=0, movable=False,
            pen=pg.mkPen(color=QColor(Qt.blue),
            width = 2, style=Qt.DashLine),
            label='{value:0.1f}',
            labelOpts={'position':0.05, 'color': (255,255,255),
                       'movable': False, 'fill': (0, 0, 200, 100)})
        #self.hLine.setPos(pg.Point(0.0, 10.0))
        self.hLine.setValue(5)
        self.hLine.setZValue(20)
        self.w.plt34.addItem(self.hLine, ignoreBounds=True)

        # вертикальная штриховая линия текущей точки position/position_actual
        self.vLine = pg.InfiniteLine(angle=90, movable=False,
            pen=pg.mkPen(color=QColor(Qt.blue),
            width = 2, style=Qt.DashLine),
            label='0.0',
            labelOpts={'position':0.95, 'color': (255,255,255),
                       'movable': False, 'fill': (0, 0, 200, 100)})

        self.vLine.setValue(20)
        self.vLine.setZValue(1)
        self.w.plt34.addItem(self.vLine, ignoreBounds=True)

        font=QtGui.QFont()
        font.setPixelSize(20)

        # тест маркеров
        pen1 = pg.mkPen(color=QColor(Qt.blue),
        width = 2, style=Qt.SolidLine)
        self.plot_f1f2 = self.w.plt34.plot([0, 200], [7, 3], pen = pen1)

        self.plot_load_data=[[], []]
        pen2 = pg.mkPen(color=QColor(Qt.darkCyan),
        width = 2, style=Qt.SolidLine)
        self.plot_current_load = self.w.plt34.plot(pos=self.plot_load_data, pen = pen2)
        self.plot_torque_data=[[], []]

        # выделить пины в отдельные объекты, чтобы каждый раз не тратить время
        # на выборку из словаря
        self.position_actual_pin34 = self.VCP_halpins_float['position_actual-pin34']
        self.position_pin34 = self.VCP_halpins_float['position-pin34']
        self.load_actual_pin34 = self.VCP_halpins_float['load_actual-pin34']
        self.load_pin34 = self.VCP_halpins_float['load-pin34']
        self.torque_actual_pin34 = self.VCP_halpins_float['torque_actual-pin34']
        self.torque_pin34 = self.VCP_halpins_float['torque-pin34']
        self.dsp_pin34 = self.VCP_halpins_float['dsp-pin34']
        self.f1_pin34 = self.VCP_halpins_float['f1-pin34']
        self.f2_pin34 = self.VCP_halpins_float['f2-pin34']
        self.omega_actual_pin34 = self.VCP_halpins_float['omega_actual-pin34']

        # после готовности графика - связать его с потоком данных от пинов
        self.position_actual_pin34.value_changed.connect(self.position_actual_changed)
        self.position_pin34.value_changed.connect(lambda:(
            self.vLine.label.setFormat('%01d' % (self.position_actual_pin34.get()) + '\n'
                                            + '(%01d)' % (self.position_pin34.get()))
            ))

        self.load_actual_pin34.value_changed.connect(self.load_actual_changed)
        self.load_pin34.value_changed.connect(self.load_changed)

        self.torque_actual_pin34.value_changed.connect(self.torque_actual_changed)
        self.torque_pin34.value_changed.connect(self.torque_changed)

        self.dsp_pin34.value_changed.connect(lambda:(
            self.w.plt34.setXRange(0.0, self.dsp_pin34.get()),
            self.plot_f1f2.setData([0.0, self.dsp_pin34.get()],
                                   [self.f1_pin34.get(), self.f2_pin34.get()])
            ))

        self.f1_pin34.value_changed.connect(lambda:(
            self.w.plt34.setYRange(min(0.0, self.f2_pin34.get(), self.f1_pin34.get())*1.2,
                                   max(0.0, self.f2_pin34.get(), self.f1_pin34.get())*1.2),
            self.plot_f1f2.setData([0.0, self.dsp_pin34.get()],
                                   [self.f1_pin34.get(), self.f2_pin34.get()])
            ))

        self.f2_pin34.value_changed.connect(lambda:(
            self.w.plt34.setYRange(min(0.0, self.f2_pin34.get(), self.f1_pin34.get())*1.2,
                                   max(self.f2_pin34.get(), self.f1_pin34.get())*1.2),
            self.plot_f1f2.setData([0.0, self.dsp_pin34.get()],
                                   [self.f1_pin34.get(), self.f2_pin34.get()])
            ))

        self.w.btnClearPlot34.clicked.connect(self.onBtnClearPlot_clicked)
        self.w.btnShowForce34.clicked.connect(self.onBtnShowForce_clicked)
        self.w.btnShowTorque34.clicked.connect(self.onBtnShowTorque_clicked)
        #self.w.btnTestPlot.clicked.connect(self.update_position)
        # курсор на графике https://stackoverflow.com/questions/50512391/can-i-share-the-crosshair-with-two-graph-in-pyqtgraph-pyqt5
        # https://stackoverflow.com/questions/52410731/drawing-and-displaying-objects-and-labels-over-the-axis-in-pyqtgraph-how-to-do
        return

    def load_actual_changed(self):
        self.plot_load_data[0].append(self.position_actual_pin34.get())
        self.plot_load_data[1].append(self.load_actual_pin34.get())

        if self.w.btnShowForce34.isChecked():
            self.hLine.setValue(self.load_actual_pin34.get())
            self.hLine.label.setFormat('%01d' % (self.load_actual_pin34.get()) + '\n'
                                       + '(%01d)' % (self.load_pin34.get()))
            self.plot_current_load.setData(x=self.plot_load_data[0],y=self.plot_load_data[1])
        return

    def load_changed(self):
        if self.w.btnShowForce34.isChecked():
            self.hLine.label.setFormat('%01d' % (self.load_actual_pin34.get()) + '\n'
                                       + '(%01d)' % (self.load_pin34.get()))

        return

    def torque_actual_changed(self):
        self.plot_torque_data[0].append(self.position_actual_pin34.get())
        self.plot_torque_data[1].append(self.torque_actual_pin34.get())
        if self.w.btnShowTorque34.isChecked():
            self.hLine.setValue(self.torque_actual_pin34.get()),
            self.hLine.label.setFormat('%01d' % (self.torque_actual_pin34.get()) + '\n'
                                            + '(%01d)' % (self.torque_pin34.get())),
            self.plot_current_load.setData(x=self.plot_torque_data[0],y=self.plot_torque_data[1])
        return

    def torque_changed(self):
        if self.w.btnShowTorque34.isChecked():
            self.hLine.label.setFormat('%01d' % (self.torque_actual_pin34.get()) + '\n'
                                       + '(%01d)' % (self.torque_pin34.get()))
        return

    def position_actual_changed(self):
        self.vLine.setValue(self.position_actual_pin34.get()),
        self.vLine.label.setFormat('%01d' % (self.position_actual_pin34.get()) + '\n'
                                        + '(%01d)' % (self.position_pin34.get()))

        self.plot_load_data[0].append(self.position_actual_pin34.get())
        self.plot_load_data[1].append(self.load_actual_pin34.get())

        self.plot_torque_data[0].append(self.position_actual_pin34.get())
        self.plot_torque_data[1].append(self.torque_actual_pin34.get())

        if self.w.btnShowForce34.isChecked():
            self.plot_current_load.setData(x=self.plot_load_data[0], y=self.plot_load_data[1])
        elif self.w.btnShowTorque34.isChecked():
            self.plot_current_load.setData(x=self.plot_torque_data[0], y=self.plot_torque_data[1])
        return

    def onBtnClearPlot_clicked(self):
        self.plot_load_data = [[],[]]
        self.plot_torque_data = [[],[]]
        if self.w.btnShowForce34.isChecked():
            self.hLine.setValue(self.load_actual_pin34.get()),
            self.hLine.label.setFormat('%01d' % (self.load_actual_pin34.get()) + '\n'
                                            + '(%01d)' % (self.load_pin34.get()))
            self.plot_current_load.setData(x=self.plot_load_data[0], y=self.plot_load_data[1])
        elif self.w.btnShowTorque34isChecked():
            self.hLine.setValue(self.torque_actual_pin34.get()),
            self.hLine.label.setFormat('%01d' % (self.torque_actual_pin34.get()) + '\n'
                                            + '(%01d)' % (self.torque_pin34.get()))
            self.plot_current_load.setData(x=self.plot_torque_data[0], y=self.plot_torque_data[1])
        return

    def onBtnShowForce_clicked(self, ischecked):
        if ischecked:
            self.w.plt34.setLabel('left', 'F [кгс]')
            self.hLine.setValue(self.load_actual_pin34.get()),
            self.hLine.label.setFormat('%01d' % (self.load_actual_pin34.get()) + '\n'
                                            + '(%01d)' % (self.load_pin34.get()))
            self.plot_current_load.setData(x=self.plot_load_data[0], y=self.plot_load_data[1])
        else:
            self.w.plt34.setLabel('left', 'T [Н*м]')
            self.hLine.setValue(self.torque_actual_pin34.get()),
            self.hLine.label.setFormat('%01d' % (self.torque_actual_pin34.get()) + '\n'
                                            + '(%01d)' % (self.torque_pin34.get()))
            self.plot_current_load.setData(x=self.plot_torque_data[0], y=self.plot_torque_data[1])
        return

    def onBtnShowTorque_clicked(self, ischecked):
        if ischecked:
            self.w.plt34.setLabel('left', 'T [Н*м]')
            self.hLine.setValue(self.torque_actual_pin34.get()),
            self.hLine.label.setFormat('%01d' % (self.torque_actual_pin34.get()) + '\n'
                                            + '(%01d)' % (self.torque_pin34.get()))
            self.plot_current_load.setData(x=self.plot_torque_data[0], y=self.plot_torque_data[1])
        else:
            self.w.plt34.setLabel('left', 'F [кгс]')
            self.hLine.setValue(self.load_actual_pin34.get()),
            self.hLine.label.setFormat('%01d' % (self.load_actual_pin34.get()) + '\n'
                                            + '(%01d)' % (self.load_pin34.get()))
            self.plot_current_load.setData(x=self.plot_load_data[0], y=self.plot_load_data[1])
        return

    def pinCnagedCallback(self, data):
        halpin_name = self.w.sender().text()

        # соответствие пинов float и табличек, на которых нужно отображать значение
        halpins_labels_match_precision2 = { # отображать с точностью 2 знака после запятой
            }

        if(halpin_name in halpins_labels_match_precision2):
            halpin_value = self.hal[halpin_name]
            halpins_labels_match_precision2[halpin_name].setText("{:10.2f}".format(halpin_value))

        halpins_labels_match_precision1 = { # отображать с точностью 1 знак после запятой

            #TODO для формы 3.4
            'position-pin34':self.w.lblPosition34,
            'position_actual-pin34':self.w.lblPosition_Actual34,
            'load-pin34':self.w.lblLoad34,
            'load_actual-pin34':self.w.lblLoad_Actual34,

            # "таблица" с диодами и надписями на Форме 3.4
            # убрали из ТЗ 2 апреля 'torque_error_value':self.w.lblTorque_Error_Value34,
            # убрали из ТЗ 2 апреля 'torque_error_value_max':self.w.lblTorque_Error_Value_Max34,
            # убрали из ТЗ 2 апреля 'torque1_error_value':self.w.lblTorque1_Error_Value34,
            # убрали из ТЗ 2 апреля 'torque1_error_value_max':self.w.lblTorque1_Error_Value_Max34,
            'load_error_value-pin34':self.w.lblLoad_Error_Value34,
            'load_error_value_max-pin34':self.w.lblLoad_Error_Value_Max34,
            # убрали из ТЗ 2 апреля 'load_overload_value':self.w.lblLoad_Overload_Value34,
            # убрали из ТЗ 2 апреля 'load_overload_value_max':self.w.lblLoad_Overload_Value_Max34,
            'load_temperature-pin34':self.w.lblLoad_Temperature34,
            'load_temperature_max-pin34':self.w.lblLoad_Temperature_Max34,
            'pos_error_value-pin34':self.w.lblPos_Error_Value34,
            'pos_error_value_max-pin34':self.w.lblPos_Error_Value_Max34,
            # убрали из ТЗ 2 апреля 'pos_overload_value':self.w.lblPos_Overload_Value34,
            # убрали из ТЗ 2 апреля 'pos_overload_value_max':self.w.lblPos_Overload_Value_Max34,
            'pos_temperature-pin34':self.w.lblPos_Temperature34,
            'pos_temperature_max-pin34':self.w.lblPos_Temperature_Max34,
            'torque_max-pin34':self.w.lblTorque_Max34 }

        if(halpin_name in halpins_labels_match_precision1):
            halpin_value = self.hal[halpin_name]
            halpins_labels_match_precision1[halpin_name].setText("{:10.1f}".format(halpin_value))

        halpins_labels_int = {
            'i-pin34':self.w.lblI34,
            'N-pin34':self.w.lblN34 }

        if(halpin_name in halpins_labels_int):
            halpin_value = self.hal[halpin_name]
            halpins_labels_int[halpin_name].setText(str(halpin_value))

        return
        #print "Test pin value changed to:" % (data) # ВЫВОДИТ ВСЕГДА 0 - ВИДИМО ОШИБКА В ДОКУМЕНТАЦИИ
        #print 'halpin object =', self.w.sender()
        #print 'Halpin type: ',self.w.sender().get_type()
    
    approx_points = [x * 35.0 for x in range(0, 10)]
    def onSpnNofPoints(self, p_new_value):
        max_points = p_new_value # self.w.spnNofPoints.value()
        max_travel = self.w.spnDsp34.value()
        multiplier = max_travel/p_new_value
        self.approx_points = [x * multiplier for x in range(0, p_new_value)]
        self.approx_points[0] = 0.0;
        self.approx_points[-1] = max_travel;
        self.hal['n_of_points-pin34'] = p_new_value
        return
    
    def onSpnTerminalEffects(self, p_new_value):
        self.hal['position_terminal-pin34']=p_new_value
        return

    def onBtnGetApprox(self):
        '''
        Расчёт аппроксимирующих функцию по массиву ошибок после пробного хода
        '''

        # сбор показаний в массив
        tmp_n_of_points = self.w.spnNofPoints.value()
        tmp_terminal_eff = self.w.spnTerminalEffects.value()
        tmp_travel_max = self.w.spnDsp34.value()
        err_positions = np.linspace(tmp_terminal_eff, tmp_travel_max - tmp_terminal_eff, num=tmp_n_of_points)
        print "err_positions ", err_positions
        err_pos_array = np.array([])
        err_neg_array = np.array([])
        for i in range(tmp_n_of_points):
            err_pos_array = np.append(err_pos_array, self.hal['err_pos_'+str(i)])
            err_neg_array = np.append(err_neg_array, self.hal['err_neg_'+str(i)])
        print "err_pos_array ", err_pos_array
        print "err_neg_array ", err_neg_array
        # метод наименьших квадратов
        #m=np.vstack((err_positions**2,err_positions,np.ones(tmp_n_of_points))).T

        features = np.concatenate((np.vstack(np.ones(tmp_n_of_points)),
            np.vstack(err_positions),
            np.vstack(err_positions**2)), axis = 1)
        determinants = np.linalg.lstsq(features, err_pos_array)[0]
        print "approx_pos = ", determinants[2],"x**2+",determinants[1],"x+",determinants[0]
        print determinants
        # передача подобранных коэффициентов в аппроксиматор
        self.hal['kpos1'] = determinants[2]
        self.hal['kpos2'] = determinants[1]
        self.hal['kpos3'] = determinants[0]

        determinants = np.linalg.lstsq(features, err_neg_array)[0]
        print "approx_neg = ", determinants[2],"x**2+",determinants[1],"x+",determinants[0]
        print determinants
        self.hal['kneg1'] = determinants[2]
        self.hal['kneg2'] = determinants[1]
        self.hal['kneg3'] = determinants[0]
        return

    def onRODOS_changed(self, state, pinname, number, turn_on):
        #INFO http://linuxcnc.org/docs/2.8/html/gui/qtvcp_code_snippets.html#_add_hal_pins_that_call_functions

        if not self.hal[pinname]: # исключить обратный фронт сигнала
            print "*** onRODOS_changed, нисходящий фронт, return"
            return

        if not state:
            print "*** onRODOS_changed, not state, return"
            return

        try:
            return_code = subprocess.call("sudo " + self.RODOS_PATH + " -a" + " --c"+str(number-1) + (" 128" if turn_on else " 0"), shell=True)
            print "*** subprocess.call(sudo", self.RODOS_PATH, " --c"+str(number-1),("128" if turn_on else "0"), ") returns ", return_code
        except Exception as exc:
            print "***Ошибка при запуске RODOS4. ", exc
        pass

        return

    #def append_data(self, x, y):
    #    self.data[0][self.current_plot_n] = x
    #    self.data[1][self.current_plot_n] = y
    #    self.current_plot_n += 1
    #    if(self.current_plot_n >= 10000):
    #        self.current_plot_n = 0 # логика кольцевого буфера
    #    return

    #def update_plot(self):
    #    # self.vLine.setValue(???)
    #    # self.hLine.setValue(???)
    #    # self.plot_f1f2.setData(???)
    #    # self.plot_current.setData(???)
    #    # if(self.current_plot_n < 20):
    #    #     #print "*** plot < 20"
    #    #     self.w.plt34.plot(self.data[0][0:self.current_plot_n],
    #    #                       self.data[1][0:self.current_plot_n],
    #    #                       clear = True)
    #    # else:
    #    #     #print "*** plot >= 20"
    #    #     self.w.plt34.plot(self.data[0][self.current_plot_n-20:self.current_plot_n],
    #    #                       self.data[1][self.current_plot_n-20:self.current_plot_n],
    #    #                       clear=True)
    #    return

    def init_datalog(self, datalogfilename):
        self.datalogfile = None
        self.datalogbuffer = []
        try:
            self.datalogfile = open(datalogfilename,"w")
            self.w.btnShowResult34.setEnabled(True)
        except Exception as exc:
            self.datalogfile = None
            QMessageBox.critical(self.w, 'Ошибка',
            ("Невозможно открыть файл лога " + datalogfilename
             + " для вывода данных. Код ошибки " + exc
             + ". Запись не будет производиться."),
            QMessageBox.Yes)
            self.w.btnShowResult34.setEnabled(False)
            return

        self.datalogfile.write("Модель: " + self.MODEL + "\n")
        self.datalogfile.write("Номер изделия: " + self.PART + "\n")
        self.datalogfile.write("Дата: " + self.DATE + "\n")
        self.datalogfile.flush()

        self.log_permit_pin34 = self.VCP_halpins_bit['log_permit-pin34'][0]
        self.append_buffer_pin34 = self.VCP_halpins_bit['append_buffer-pin34'][0]
        self.append_title_pin34 = self.VCP_halpins_bit['append_title-pin34'][0]
        self.append_file_pin34 = self.VCP_halpins_bit['append_file-pin34'][0]

        self.VCP_halpins_bit['append_buffer-pin34'][0].value_changed.connect(self.append_buffer)
        self.VCP_halpins_bit['append_title-pin34'][0].value_changed.connect(self.append_title)
        self.VCP_halpins_bit['append_file-pin34'][0].value_changed.connect(self.append_file)
        return

    def append_file(self):
        if self.datalogfile is None:
            return
        if self.datalogfile.closed:
            return
        if not self.log_permit_pin34.get():
            return
        if not self.append_file_pin34.get(): # запись только по восходящему фронту
            return

        for itm in self.datalogbuffer:
            self.datalogfile.write(
                itm[0].strftime("%d.%m.%Y %H:%M:%S") + '\t' # time_current;
                + '%01d' % itm[1] + '\t' # position_actual
                + '%01d' % itm[2] + '\t' #omega_actual
                + '%01d' % itm[3] + '\t' #load_actual
                + '%01d' % itm[4] + '\n') #torque_actual

        self.datalogfile.flush()
        self.datalogbuffer = []
        self.onBtnClearPlot_clicked()
        return

    def append_buffer(self):
        if self.datalogfile is None:
            return
        if self.datalogfile.closed:
            return
        if not self.log_permit_pin34.get():
            return
        if not self.append_buffer_pin34.get(): # запись только по восходящему фронту
            return

        #Вектор параметров состояния: (time_current; position_actual; omega_actual;
        #load_actual; torque_actual)
        self.datalogbuffer.append([
            datetime.now(),
            self.position_actual_pin34.get(),
            self.omega_actual_pin34.get(),
            self.load_actual_pin34.get(),
            self.torque_actual_pin34.get()])

        return

    def append_title(self):
        if self.datalogfile is None:
            return
        if self.datalogfile.closed:
            return
        if not self.log_permit_pin34.get():
            return
        if not self.append_title_pin34.get():  # запись только по восходящему фронту
            return

        # промежуточный заголовок в виде:
        # Время запуска: time
        # Нагрузка в начальном положении: f1
        # Нагрузка в конечном положении: f1

        self.datalogfile.flush()
        self.datalogfile.write("\n")
        self.datalogfile.write("Время запуска: "
                                + datetime.now().strftime("%d/%m/%Y %H:%M:%S") + "\n")
        self.datalogfile.write("Нагрузка в начальном положении: " + '%01d' % (self.f1_pin34.get()) + "\n")
        self.datalogfile.write("Нагрузка в конечном положении: " + '%01d' % (self.f2_pin34.get()) + "\n")
        self.datalogfile.write("\n")
        self.datalogfile.flush()
        return

    #def flush_to_log(self):
    #    logfile = open('temp_log_form4.log', 'w')
    #    #Заголовок лога
    #    logfile.write('Модель: ', self.MODEL, '\n')
    #    logfile.write('Номер изделия: ', self.PART, '\n')
    #    logfile.write('Дата: ', self.DATE, '\n')
    #    logfile.write('\n')
    #    for i in range(self.current_plot_n):
    #        logfile.write(self.data[0][i], self.data[1][i])
    #    logfile.close()
    #    return

    #def on_siggen_test_read_pin_value_changed(self, data):
    #    return
    #    #print("*** siggen pin data: ", data)
    #    #print("*** siggen pin: ", self.siggen_test_read_pin.get())
    #    #print("*** siggen.0.sine directly", hal.get_value("siggen.0.sine"))

    #TODO в принципе функция не нужна, т.к. linuxcnc сам поддерживает передачу параметров из ini
    def load_ini(self):
        ini_control_match_dict = {# для формы 3.4
            'NOM_TRAVEL' : [self.w.sldDsp34, self.w.spnDsp34],
            'NOM_OMEGA': [self.w.sldOmg34, self.w.spnOmg34],
            'NOM_ACCEL_COEFF': [self.w.sldAccel_Coeff34, self.w.spnAccel_Coeff34],
            'NOM_F1': [self.w.sldF1_34, self.w.spnF1_34],
            'NOM_F2': [self.w.sldF2_34, self.w.spnF2_34]
        }

        #self.TYPE = INFO.INI.findall("BALLSCREWPARAMS", "TYPE")[0]
        #print "*** self.TYPE = ", self.TYPE
        self.TYPE = INFO.INI.findall("BALLSCREWPARAMS", "TYPE")[0]
        self.DATALOGFILENAME = INFO.INI.findall("BALLSCREWPARAMS", "LOGFILE")[0]
        self.MODEL = INFO.INI.findall("BALLSCREWPARAMS", "MODEL")[0]
        self.DATE = INFO.INI.findall("BALLSCREWPARAMS", "DATE")[0]
        self.PART = INFO.INI.findall("BALLSCREWPARAMS", "PART")[0]

        for key, controls in ini_control_match_dict.items():
            print '***controls[0] = ', controls[0].objectName()
            print '***controls[1] = ', controls[1].objectName()
            controls[0].setMinimum(int(float(INFO.INI.findall("BALLSCREWPARAMS", key+'_MIN')[0])*100))
            controls[0].setMaximum(int(float(INFO.INI.findall("BALLSCREWPARAMS", key+'_MAX')[0])*100))
            controls[0].setValue(int(float(INFO.INI.findall("BALLSCREWPARAMS", key)[0])*100))
            controls[1].setMinimum(float(INFO.INI.findall("BALLSCREWPARAMS", key+'_MIN')[0]))
            controls[1].setMaximum(float(INFO.INI.findall("BALLSCREWPARAMS", key+'_MAX')[0]))
            controls[1].setValue(float(INFO.INI.findall("BALLSCREWPARAMS", key)[0]))

        #TODO обработка ошибок и исключений: 1) нет файла - сообщение и заполнение по умолчанию, создание конфига
        #TODO обработка ошибок и исключений: 2) нет ключей в конфиге - сообщение и заполнение по умолчанию

    def update_ini(self):
        # список на замену
        # replacelist = [[ur'^123'.encode(), ur'123'.encode()]]
        replacelist = [[ur"(NOM_TRAVEL\s*\=)\s*(\d+(.\d*){0,1})",
                        ur"\1 {:.1f}".format(self.w.spnDsp34.value())],
                       [ur"(NOM_OMEGA\s*\=)\s*(\d+(.\d*){0,1})",
                        ur"\1 {:.1f}".format(self.w.spnOmg34.value())],
                       [ur'(NOM_ACCEL_COEFF\s*\=)\s*(\d+(.\d*){0,1})',
                        ur"\1 {:.1f}".format(self.w.spnAccel_Coeff34.value())],
                       [ur"(NOM_F1\s*\=)\s*(\d+(.\d*){0,1})",
                        ur"\1 {:.1f}".format(self.w.spnF1_34.value())],
                       [ur"(NOM_F2\s*\=)\s*(\d+(.\d*){0,1})",
                        ur"\1 {:.1f}".format(self.w.spnF2_34.value())]]

        # путь к текущему INI-файлу
        inifilename = INFO.INIPATH# имя ini-файла
        print "*** inifilename = ", inifilename

        # открыть и считать
        inifile = io.open(inifilename, "r", encoding='utf8')
        #TODO обработка открыт/не открыт
        inilines = inifile.readlines()
        inifile.close()

        print "***inilines=", inilines

        # список поле - GUI-элемент
        for line_n in range(len(inilines)): # перечислить все строки INI-файла
            for replace_item in replacelist: # в каждой строке поиск
                tmp_line = re.sub(replace_item[0], replace_item[1], inilines[line_n])
                if not tmp_line == inilines[line_n]:
                    inilines[line_n] = tmp_line
                    print "***выполнена замена ", inilines[line_n]

        inifile2 = io.open(inifilename, "w", encoding='utf8')
        #TODO обработка ошибки открыт/не открыт
        inilines = inifile2.writelines(inilines)
        inifile2.close()
    
################################
# required handler boiler code #
################################

def get_handlers(halcomp, widgets, paths):
     return [HandlerClass(halcomp, widgets, paths)]
