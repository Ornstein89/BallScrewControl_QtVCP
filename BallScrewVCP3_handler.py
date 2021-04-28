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
import sys, os, configparser, subprocess, random, io, copy
import codecs
import re
from datetime import datetime

# пакеты linuxcnc
import linuxcnc, hal # http://linuxcnc.org/docs/html/hal/halmodule.html

# пакеты GUI
from PyQt5 import QtCore, QtWidgets, QtGui, Qt
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QLabel
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
# **** INSTANTIATE LIBRARIES SECTIO **** #
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
        self.start_log(self.DATALOGFILENAME)
        # self.gcodes.setup_list() инструкция нужна только для отображения справочного списка команд

        #fov = FocusOverlay(self)
        #fov.show()

    def processed_key_event__(self,receiver,event,is_pressed,key,code,shift,cntrl):
        if event.key() == Qt.Key_Left and self.w.btnJog_Minus33.isEnabled():
            if is_pressed and not self.w.btnJog_Minus33.isDown():
                self.w.btnJog_Minus33.setDown(True)
                #self.w.btnJog_Minus33.click(True)
                self.w.btnJog_Minus33.pressed.emit()
                #self.w.btnJog_Minus33.setCheckable(True)
                #self.w.btnJog_Minus33.setChecked(True)
            elif self.w.btnJog_Minus33.isDown():
                self.w.btnJog_Minus33.setDown(False)
                #self.w.btnJog_Minus33.click(False)
                self.w.btnJog_Minus33.released.emit()
                #self.w.btnJog_Minus33.setChecked(False)
                #self.w.btnJog_Minus33.setCheckable(False)
            #print '*** Qt.Key_Left'
            # event.accept()

        if event.key() == Qt.Key_Right and self.w.btnJog_Plus33.isEnabled():
            if is_pressed and not self.w.btnJog_Plus33.isDown():
                self.w.btnJog_Plus33.setDown(True)
                self.w.btnJog_Plus33.pressed.emit()
                # self.w.btnJog_Plus33.click(True)
                # self.w.btnJog_Plus33.press()
                # self.w.btnJog_Plus33.setCheckable(True)
                # self.w.btnJog_Plus33.setChecked(True)
            elif self.w.btnJog_Plus33.isDown():
                self.w.btnJog_Plus33.setDown(False)
                self.w.btnJog_Plus33.released.emit()
                # self.w.btnJog_Plus33.click(True)
                # self.w.btnJog_Plus33.release()
                # self.w.btnJog_Plus33.setChecked(False)
                # self.w.btnJog_Plus33.setCheckable(False)

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
            'position-pin33':None,
            'position_actual-pin33':None,
            'load-pin33':None,
            'load_actual-pin33':None,
            'dsp_idle-pin33':None,
            'load_error_value-pin33':None,
            'load_error_value_max-pin33':None,
            'load_overload_value-pin33':None,
            'load_overload_value_max-pin33':None,
            'load_temperature-pin33':None,
            'load_temperature_max-pin33':None,
            'pos_error_value-pin33':None,
            'pos_error_value_max-pin33':None,
            'pos_overload_value-pin33':None,
            'pos_overload_value_max-pin33':None,
            'pos_temperature-pin33':None,
            'pos_temperature_max-pin33':None,
            'torque_extremal_last-pin33':None,
            'torque_extremal_max-pin33':None,
            'torque_actual-pin33':None,
            'torque_estimated-pin33':None,

            'position_0-pin33':None,
            'torque_extremal_0-pin33':None,
            'position_1-pin33':None,
            'torque_extremal_1-pin33':None,
            'position_2-pin33':None,
            'torque_extremal_2-pin33':None,
            'position_3-pin33':None,
            'torque_extremal_3-pin33':None,
            'position_4-pin33':None,
            'torque_extremal_4-pin33':None
        }

        self.VCP_halpins_bit = {
            'append_buffer-pin33':[None, None],
            'append_file-pin33':[None, None],

            'active_0-pin':[None, self.guiStatesSwitch],
            'active_1-pin':[None, self.guiStatesSwitch],
            'active_2-pin':[None, self.guiStatesSwitch],
            'active_3-pin':[None, self.guiStatesSwitch],
            'active_4-pin':[None, self.guiStatesSwitch],
            'active_5-pin':[None, self.guiStatesSwitch],

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
            tmp_pin = self.hal.newpin(key, hal.HAL_FLOAT, hal.HAL_IN)
            self.VCP_halpins_float[key] = tmp_pin
            tmp_pin.value_changed.connect(lambda s: self.pinLabelsChanged(s)) # к каждому пину привязывается своя label

        for key in self.VCP_halpins_bit:
            tmp_pin = self.hal.newpin(key, hal.HAL_BIT, hal.HAL_IN)
            self.VCP_halpins_bit[key][0] = tmp_pin
            if self.VCP_halpins_bit[key][1] is not None:
                tmp_pin.value_changed.connect(self.VCP_halpins_bit[key][1])

        self.btnJog_Plus33OutPin = self.hal.newpin('btnJog_Plus33', hal.HAL_BIT, hal.HAL_OUT)
        self.btnJog_Minus33OutPin = self.hal.newpin('btnJog_Minus33', hal.HAL_BIT, hal.HAL_OUT)

        return
        
    # def onBtnTempShow31(self):
    #     self.w.stackedWidget.setCurrentIndex(5)
    #     pass
    #
    # def onBtnTempShow32(self):
    #     self.w.stackedWidget.setCurrentIndex(6)
    #     pass
    #
    # def onBtnTempShow33(self):
    #     self.w.stackedWidget.setCurrentIndex(7)
    #     pass
    #s
    # def onBtnTempShow34(self):
    #     #     self.w.stackedWidget.setCurrentIndex(8)
    #     #     pass

    def onBtnLoadGCode33(self):
        # код на основе btn_load и load_code из qtdragon
        #fname = self.w.filemanager.getCurrentSelected()
        fname = QFileDialog.getOpenFileName(self.w, 'Open GCode file',
        ".","NGC (*.ngc);;Text files (*.txt);;All Files (*.*)")
        if (fname[1] is None) or (fname[0] is None):
            #TODO уведомление
            return
        elif fname[0].endswith(".ngc"):
            # self.w.cmb_gcode_history.addItem(fname) отобразить текущий файл в combobox
            # self.w.cmb_gcode_history.setCurrentIndex(self.w.cmb_gcode_history.count() - 1) отобразить текущий файл в combobox
            ACTION.OPEN_PROGRAM(fname[0])
            #self.add_status("Loaded program file : {}".format(fname))
            #self.w.main_tab_widget.setCurrentIndex(TAB_MAIN)
            #STATUS.emit('update-machine-log', "Loaded program file : {}".format(fname), 'TIME')
            print "*** LOADED"
        #else:
            #self.add_status("Unknown or invalid filename")
            #STATUS.emit('update-machine-log', "Unknown or invalid filename", 'TIME')
            #print "*** ERROR LOAD FILE"

    def onBtnSaveGCode33(self):
        replacements = [['{{dsp_idle}}', '{:.1f}'.format(self.w.spnDsp_Idle33.value())],
            ['{{vel_idle}}', '{:.1f}'.format(self.w.spnVel_Idle33.value())],
            ['{{accel_idle}}', '{:.1f}'.format(self.w.spnAccel_Idle33.value())],
            ['{{load}}', '{:.1f}'.format(self.w.spnLoad33.value())],
            ['{{pos_measure}}', '{:.1f}'.format(self.w.spnPos_Measure33.value())],
            ['{{dsp_measure}}', '{:.1f}'.format(self.w.spnDsp_Measure33.value())],
            ['{{vel_measure}}', '{:.1f}'.format(self.w.spnVel_Measure33.value())],
            ['{{accel_measure}}', '{:.1f}'.format(self.w.spnAccel_Measure33.value())]]

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

    def onBtnClearPlot33(self):
        #TODO
        pass

    def onBtnMDI(self):
        # способ 1, через linuxcnc
        # linuxcnc.command().mode(linuxcnc.MODE_MDI)
        # linuxcnc.command().wait_complete() # wait until mode switch executed
        # linuxcnc.command().mdi(self.w.mdiline33.text()+'\n')

        # способ 2, через QtVCP
        #try:
        #    #ACTION.SET_MDI_MODE(self) # не нужно, т.к. ACTION.CALL_MDI() уже проверяет режим
        #    ACTION.CALL_MDI(self.w.mdiline33.text()+'\n')
        #except:
        #    QMessageBox.critical(self.w, 'Ошибка',
        #    "Невозможно включить режим MDI или выполнить команду", QMessageBox.Yes)

        # способ 3
        self.w.mdiline33.submit()
        #TODO защита от ошибки "Не могу исполнить команду MDI если не найдены начала"
        return

    def guiStatesSwitch(self):
        self.w.btnHome33.setEnabled(self.hal['active_0-pin'] and STATUS.machine_is_on())

        controls_on_active1 = [ # список элементов, которые становятся активны
            self.w.btnJog_Plus33,
            self.w.btnJog_Minus33,
            self.w.chkDspModeHH_33,
            self.w.chkDspModeIZM_33]
        for control in controls_on_active1:
            control.setEnabled(self.hal['active_1-pin'] and STATUS.machine_is_on())

        self.w.chkLoad_Active_On33.setEnabled(self.hal['active_2-pin'] and STATUS.machine_is_on())
        self.w.chkLoad_Active_Off33.setEnabled(self.hal['active_2-pin'] and STATUS.machine_is_on())

        controls_on_active3 = [ # список элементов, которые становятся активны
            self.w.sldDsp_Idle33,
            self.w.spnDsp_Idle33,

            self.w.sldVel_Idle33,
            self.w.spnVel_Idle33,

            self.w.sldAccel_Idle33,
            self.w.spnAccel_Idle33,

            self.w.sldLoad33,
            self.w.spnLoad33,

            self.w.sldPos_Measure33,
            self.w.spnPos_Measure33,

            self.w.sldDsp_Measure33,
            self.w.spnDsp_Measure33,

            self.w.sldVel_Measure33,
            self.w.spnVel_Measure33,

            self.w.sldAccel_Measure33,
            self.w.spnAccel_Measure33,

            self.w.btnSaveGCode33]

        for control in controls_on_active3:
            control.setEnabled(self.hal['active_3-pin'] and STATUS.machine_is_on())

        controls_on_active4 = [
            self.w.mdiline33, self.w.btnCommand_Run33]
        for control in controls_on_active4:
            control.setEnabled(self.hal['active_4-pin'] and STATUS.machine_is_on())

        controls_on_active5 = [
            self.w.gcode_editor33, self.w.btnLoadGCode33, self.w.btnProgram_Run33]
        for control in controls_on_active5:
            control.setEnabled(self.hal['active_5-pin'] and STATUS.machine_is_on())
        return

    def onActive0Changed(self, data):
        pass

    def onActive1Changed(self, data):
        pass


    def onActive2Changed(self, data):
        pass

    def onActive3Changed(self, data):
        pass


    def onActive4Changed(self, data):
        self.w.btnCommand_Run33.setEnabled(self.hal['active_4-pin'] and STATUS.machine_is_on())

    def onActive5Changed(self, data):
        self.w.btnLoadGCode33.setEnabled(self.hal['active_5-pin'] and STATUS.machine_is_on())
        self.w.btnProgram_Run33.setEnabled(self.hal['active_5-pin'] and STATUS.machine_is_on())
        self.w.btnProgram_Stop33.setEnabled(self.hal['active_5-pin'] and STATUS.machine_is_on())
        self.w.gcode_editor33.setEnabled(self.hal['active_5-pin'] and STATUS.machine_is_on())

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

    def init_datalog(self, datalogfilename):
        self.datalogfile = None
        self.datalogbuffer = []
        try:
            self.datalogfile = open(datalogfilename,"w")
        except Exception as exc:
            self.datalogfile = None
            QMessageBox.critical(self.w, 'Ошибка',
            ("Невозможно открыть файл лога " + datalogfilename
             + " для вывода данных. Код ошибки " + exc
             + ". Запись не будет производиться."),
            QMessageBox.Yes)
            return

        self.datalogfile.write("Модель: " + self.MODEL + "\n")
        self.datalogfile.write("Номер изделия: " + self.PART + "\n")
        self.datalogfile.write("Дата: " + self.DATE + "\n")
        self.datalogfile.flush()

        self.append_buffer_pin33 = self.VCP_halpins_bit['append_buffer-pin33'][0]
        self.append_file_pin33 = self.VCP_halpins_bit['append_file-pin33'][0]

        self.append_buffer_pin33.value_changed.connect(self.append_buffer)
        self.append_file_pin33.value_changed.connect(self.append_file)
        return

    def append_file(self):
        # По сигналу append_file вектор параметров состояния записываетcя
        # в конец лог-файла в виде:
        # Время измерения: time:
        # Положение измерения: pos_measure
        # Нагрузка: load
        # Приведённый момент от нагрузки: torque_at_load
        # Момент страгивания: torque_extremal

        if self.datalogfile is None:
            return
        if self.datalogfile.closed:
            return
        if not self.append_file_pin33.get(): # запись только по восходящему фронту
            return

        for itm in self.datalogbuffer:
            self.datalogfile.write("\n")
            self.datalogfile.write("Время измерения:\t" + itm[0].strftime("%d.%m.%Y %H:%M:%S") + "\n")
            self.datalogfile.write("Положение измерения:\t" '%0.1d' % itm[1] + "\n")
            self.datalogfile.write("Нагрузка: "+ '%0.1d' % itm[2] + "\n")
            self.datalogfile.write("Приведённый момент от нагрузки: "+ '%0.1d' % itm[3] + "\n")
            self.datalogfile.write("Момент страгивания: "+ '%0.1d' % itm[4] + "\n")

        self.datalogfile.flush()
        self.datalogbuffer = []
        #self.onBtnClearPlot_clicked()
        return

    def append_buffer(self):
        if self.datalogfile is None:
            return
        if self.datalogfile.closed:
            return
        if not self.append_buffer_pin33.get(): # запись только по восходящему фронту
            return

        #Вектор параметров состояния: (time; pos_measure; load; torque_at_load;
        #torque_extremal)

        self.datalogbuffer.append([
            datetime.now(),
            self.pos_measure_pin33.get(),
            self.load_pin33.get(),
            self.torque_at_load_pin33.get(),
            self.torque_extremal_pin33.get()])

        return

    #####################
    # GENERAL FUNCTIONS #
    #####################
    def init_gui(self):
        self.w.setWindowIcon(QIcon("BallScrewControlIcon.png"))
        self.load_ini()
        self.init_led_colors()
        #self.w.lblTest = QHalLabel()
        #self.w.lblTest.setText("!!!HAL Label!!!")
        # self.w.gridLayout_29.addWidget(self.w.lblTest, 3, 2)
        self.init_plot()

        STATUS.connect('state-estop',
                       lambda w: (self.w.btnDevice_On33.setEnabled(False)))
        STATUS.connect('state-estop-reset',
                       lambda w: (self.w.btnDevice_On33.setEnabled(not STATUS.machine_is_on())))

        self.w.btnDevice_On33.clicked.connect(lambda x: ACTION.SET_MACHINE_STATE(True))
        self.w.btnDevice_Off33.clicked.connect(lambda x: ACTION.SET_MACHINE_STATE(False))

        #self.w.btnCommand_Run33.clicked.connect(labmda x: ACTION.CALL_MDI())


        # сделать чекбоксы исключающими
        #self.w.chkDspModeHH_33..connect(self.w.chkDspModeIZM_33.setChecked(not self.w.chkDspModeHH_33.isChecked()))

        STATUS.connect('state-on', lambda _: (self.w.btnDevice_On33.setEnabled(False),
                                              self.guiStatesSwitch()))

        STATUS.connect('state-off', lambda _:(self.w.btnDevice_On33.setEnabled(STATUS.estop_is_clear()),
                                              self.guiStatesSwitch()))

        self.w.btnTest.clicked.connect(self.testUpdatePlot)

        # включение MODE_MANUAL перед использованием JOG
        self.w.btnJog_Plus33.pressed.connect(lambda : (
            ACTION.ensure_mode(linuxcnc.MODE_MANUAL),
            self.btnJog_Plus33OutPin.set(1)))
        self.w.btnJog_Plus33.released.connect(lambda : (
            ACTION.ensure_mode(linuxcnc.MODE_MANUAL),
            self.btnJog_Plus33OutPin.set(0)))

        self.w.btnJog_Minus33.pressed.connect(lambda : (
            ACTION.ensure_mode(linuxcnc.MODE_MANUAL),
            self.btnJog_Minus33OutPin.set(1)))
        self.w.btnJog_Minus33.released.connect(lambda : (
            ACTION.ensure_mode(linuxcnc.MODE_MANUAL),
            self.btnJog_Minus33OutPin.set(0)))

        # масштабирование с помощью пинов *-scale
        # (команды setp в hal-файле недостаточно - слайдер не масштабирует,
        # пока не сдвинуть вручную)
        sliders_to_scale = [
            self.w.sldDsp_Idle33, self.w.sldVel_Idle33, self.w.sldAccel_Idle33,
            self.w.sldLoad33, self.w.sldPos_Measure33, self.w.sldDsp_Measure33,
            self.w.sldVel_Measure33, self.w.sldAccel_Measure33]

        for slider_i in sliders_to_scale:
            slider_i.hal_pin_scale.set(0.01)
            slider_i.hal_pin_f.set(slider_i.value()*0.01)

        # экран-заглушка для графика пока не получены данные с устройства
        # self.w.plot_overlay = QLabel(self.w.plt33)
        # self.stub_image = QPixmap("stub_screen.png")
        # self.w.plot_overlay.setPixmap(self.stub_image)

        # приведение GUI в соответствие с сигналами HAL
        self.guiStatesSwitch()

        #self.w.wgtTestPanel.hide() # убрать панель с тестовым функционалом

        self.w.overlay = FocusOverlay(self.w)
        self.w.overlay.setGeometry(0, 0, self.w.width(), self.w.height())
        self.w.overlay.hide()

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
            led.setColor(Qt.red)
            led.setOffColor(Qt.green)

        return

    def init_plot(self):
        self.w.plt33.showGrid(x = True, y = True)
        self.w.plt33.setBackground('w')
        styles = {'color':'r', 'font-size':'20px'}
        self.w.plt33.setLabel('left', 'T [Н*м]', **styles)
        self.w.plt33.setLabel('bottom', 'S [мм]', **styles)

        # дефолтное положение
        self.w.plt33.setYRange(0.0, 10)
        self.w.plt33.setXRange(0.0, 200)

        # размер шрифта числовых значений осей
        font=QtGui.QFont()
        font.setPixelSize(20)
        #plot.getAxis("bottom").tickFont = font
        self.w.plt33.getAxis("bottom").setStyle(tickFont = font)
        self.w.plt33.getAxis("left").setStyle(tickFont = font)

        # горизонтальная штриховая линия текущей точки
        self.hLineCurrent = pg.InfiniteLine(angle=0, movable=False,
            pen=pg.mkPen(color=QColor(Qt.blue),
            width = 2, style=Qt.DashLine),
            label='{value:0.1f}',
            labelOpts={'position':0.05, 'color': (255,255,255),
                       'movable': False, 'fill': (0, 0, 200, 100)})

        self.hLineCurrent.setValue(5)
        self.hLineCurrent.setZValue(1)
        self.w.plt33.addItem(self.hLineCurrent, ignoreBounds=True)

        # вертикальная штриховая линия текущей точки
        self.vLineCurrent = pg.InfiniteLine(angle=90, movable=False,
            pen=pg.mkPen(color=QColor(Qt.blue),
            width = 2, style=Qt.DashLine),
            label='0.0',
            labelOpts={'position':0.95, 'color': (255,255,255),
                       'movable': False, 'fill': (0, 0, 200, 100)})
        self.vLineCurrent.setValue(20)
        self.vLineCurrent.setZValue(1)
        self.w.plt33.addItem(self.vLineCurrent, ignoreBounds=True)

        # горизонтальная штриховая torque_estimated
        self.hTorqueEstimated = pg.InfiniteLine(angle=0, movable=False,
            pen=pg.mkPen(color=QColor(Qt.red),
            width = 2, style=Qt.DashDotLine),
            label='{value:0.1f}',
            labelOpts={'position':0.95, 'color': (255,255,255),
                       'movable': False, 'fill': (200, 0, 0, 100)})

        self.hTorqueEstimated.setValue(0.5)
        self.hTorqueEstimated.setZValue(1)
        self.w.plt33.addItem(self.hTorqueEstimated, ignoreBounds=True)

        # тест маркеров
        pen = pg.mkPen(None) # отсутствие линии между точками
        #pen = pg.mkPen(color=(255, 0, 0), width=0, style=QtCore.Qt.DashLine)
        self.xdata = [0, 0, 0, 0, 0]
        self.ydata = [0, 0, 0, 0, 0]
        self.plot_points = self.w.plt33.plot(self.xdata, self.ydata,
            symbol='x', symbolSize=30, symbolBrush=('b'))
        #self.w.plt33.setTexts(["a", "b", "d", "e", "f"])
        #self.w.plt33.updateGraph()

        # надписи над пятью точками
        self.txt_items = []
        for i in range(5):
            txt_itm = pg.TextItem(str(i), anchor=(0, 1.5))
            txt_itm.setPos(self.xdata[i], self.ydata[i])
            txt_itm.setFont(font)
            self.txt_items.append(txt_itm)
            self.w.plt33.addItem(txt_itm)
        #self.w.plt33.textItems.append(txt_item)

        # self.graphWidget.setXRange(5, 20, padding=0)
        # self.graphWidget.setYRange(30, 40, padding=0)
        # курсор на графике https://stackoverflow.com/questions/50512391/can-i-share-the-crosshair-with-two-graph-in-pyqtgraph-pyqt5
        # https://stackoverflow.com/questions/52410731/drawing-and-displaying-objects-and-labels-over-the-axis-in-pyqtgraph-how-to-do
        self.VCP_halpins_plot = [
            'position-pin33',
            'position_actual-pin33',
            'torque_actual-pin33',
            'torque_estimated-pin33',
            'dsp_idle-pin33',
            'position_0-pin33',
            'torque_extremal_0-pin33',
            'position_1-pin33',
            'torque_extremal_1-pin33',
            'position_2-pin33',
            'torque_extremal_2-pin33',
            'position_3-pin33',
            'torque_extremal_3-pin33',
            'position_4-pin33',
            'torque_extremal_4-pin33' ]
        for pin_name in self.VCP_halpins_plot:
            self.VCP_halpins_float[pin_name].value_changed.connect(self.pinUpdatePlot)

        return

    def pinLabelsChanged(self, data):
        halpin_name = self.w.sender().text()
        # отдельный пин, поставляющий float-параметр для построения графика
        #if(halpin_name == 'position-pin31'):
        #    #print "*** update and plot"
        #    self.append_data(self.current_plot_n, self.hal['position-pin31']) # добавить точку к буферу графика
        #    self.update_plot() # обновить график

        halpins_labels_match_precision1 = { # отображать с точностью 1 знак после запятой

            # На форме 3.3
            'position-pin33':self.w.lblPosition33,
            'position_actual-pin33':self.w.lblPosition_Actual33,
            'load-pin33':self.w.lblLoad33,
            'load_actual-pin33':self.w.lblLoadActual33,

            # "таблица" с диодами и надписями на Форме 3.3
            'load_error_value-pin33':self.w.lblLoad_Error_Value33,
            'load_error_value_max-pin33':self.w.lblLoad_Error_Value_Max33,
            'load_overload_value-pin33':self.w.lblLoad_Overload_Value33,
            'load_overload_value_max-pin33':self.w.lblLoad_Overload_Value_Max33,
            'load_temperature-pin33':self.w.lblLoad_Temperature33,
            'load_temperature_max-pin33':self.w.lblLoad_Temperature_Max33,

            'pos_error_value-pin33':self.w.lblPos_Error_Value33,
            'pos_error_value_max-pin33':self.w.lblPos_Error_Value_max33,
            'pos_overload_value-pin33':self.w.lblPos_Overload_Value33,
            'pos_overload_value_max-pin33':self.w.lblPos_Overload_Value_max33,
            'pos_temperature-pin33':self.w.lblPos_Temperature33,
            'pos_temperature_max-pin33':self.w.lblPos_Temperature_Max33,
            'torque_extremal_last-pin33':self.w.lblTorque_Extremal_Last33,
            'torque_extremal_max-pin33':self.w.lblTorque_Extremal_Max33
        }

        if(halpin_name in halpins_labels_match_precision1):
            halpin_value = self.hal[halpin_name]
            halpins_labels_match_precision1[halpin_name].setText("{:10.1f}".format(halpin_value))

        return
        #print "Test pin value changed to:" % (data) # ВЫВОДИТ ВСЕГДА 0 - ВИДИМО ОШИБКА В ДОКУМЕНТАЦИИ
        #print 'halpin object =', self.w.sender()
        #print 'Halpin type: ',self.w.sender().get_type()

    # def append_data(self, p_time, p_pos_measure, p_load, p_torque_at_load, p_torque_extremal):
    #     '''
    #     Функция для фиксирования новых показаний в массиве, по которому будет строиться график и записываться файл
    #     :param p_time:
    #     :param p_pos_measure:
    #     :param p_load:
    #     :param p_torque_at_load:
    #     :param p_torque_extremal:
    #     :return:
    #     '''
    #     # Вектор параметров состояния: (time; pos_measure; load; torque_at_load; torque_extremal)
    #     self.data['time'][self.current_plot_n] = p_time
    #     self.data['pos_measure'][self.current_plot_n] = p_pos_measure
    #     self.data['load'][self.current_plot_n] = p_load
    #     self.data['torque_at_load'][self.current_plot_n] = p_torque_at_load
    #     self.data['torque_extremal'][self.current_plot_n] = p_torque_extremal
    #     self.current_plot_n += 1
    #     # if(self.current_plot_n >= 10000):
    #     #     self.current_plot_n = 0 # логика кольцевого буфера
    #     return

    def testUpdatePlot(self):
        """
        self.hLineCurrent - 'torque-actual'
        self.vLineCurrent - 'position-actual'
        self.hTorqueEstimated - 'torque-estimated'
        """

        # передвинуть линии
        torque_est = random.random()*10.0
        torque_actual = torque_est * random.random()
        dsp_idle = random.random()*200.0
        current_position = dsp_idle * random.random()
        actual_position = current_position * random.random() * 0.01
        self.w.plt33.clear()
        self.hLineCurrent.setValue(torque_actual)
        #self.hLineCurrent.label.format = '%01d' % (torque_actual)

        self.vLineCurrent.setValue(dsp_idle * random.random())
        self.vLineCurrent.label.format = '%01d' % (current_position) + '\n' + '(%01d)' % (actual_position)

        self.hTorqueEstimated.setValue(torque_est)
        #self.hTorqueEstimated.label.format = '%01d' % (torque_est)

        # масштабирование X:[0 - torque-estimated*1.5], Y:[]
        self.w.plt33.setYRange(0.0, torque_est*1.5)
        self.w.plt33.setXRange(0.0, dsp_idle)
        self.txt_items[2].setPos(dsp_idle*0.3, torque_est*0.3)

    # def saveIni(self):
    #     pass

    def pinUpdatePlot(self):
        '''
        Функция для построения графика в координатах position(X)-torque(Y)
        :return:
        '''
        halpin_name = self.w.sender().text()
        #print halpin_name[18] if len(halpin_name)>18 else halpin_name[9]

        if halpin_name == 'torque_actual-pin33':
            self.hLineCurrent.setValue(float(self.hal['torque_actual-pin33']))
        elif halpin_name == 'torque_estimated-pin33':
            torque_est = float(self.hal['torque_estimated-pin33'])
            self.w.plt33.setYRange(0.0, torque_est*1.5)
            self.hTorqueEstimated.setValue(torque_est)
        elif halpin_name == 'position_actual-pin33':
            actual_position = float(self.hal['position_actual-pin33'])
            self.vLineCurrent.setValue(actual_position)
            current_position = float(self.hal['position-pin33'])
            self.vLineCurrent.label.format = '%01d' % (current_position) + '\n' + '(%01d)' % (actual_position)
        elif halpin_name == 'position-pin33':
            actual_position = float(self.hal['position_actual-pin33'])
            self.vLineCurrent.setValue(actual_position)
            current_position = float(self.hal['position-pin33'])
            self.vLineCurrent.label.format = '%01d' % (current_position) + '\n' + '(%01d)' % (actual_position)
        elif halpin_name == 'dsp_idle-pin33':
            self.w.plt33.setXRange(0.0, float(self.hal['dsp_idle-pin33']))
        elif len(halpin_name)==16:
            if (halpin_name[:9] == 'position_') and halpin_name[9].isdigit():
                #DEBUG print halpin_name
                i=int(halpin_name[9])
                xpos=float(self.hal['position_'+str(i)+'-pin33'])
                ypos=float(self.hal['torque_extremal_'+str(i)+'-pin33'])
                self.txt_items[i].setPos(xpos, ypos)
                self.txt_items[i].setText('%01d' % ypos)
                #self.w.plt33.clear()
                temp_data=self.plot_points.getData()
                temp_data[0][i]=xpos #FIXME здесь возникает ошибка
                temp_data[1][i]=ypos
                self.plot_points.setData(temp_data[0], temp_data[1])
                #self.plot_points.update()
                #self.w.plt33.update()
        elif len(halpin_name)==23:
            if (halpin_name[:16] == 'torque_extremal_') and halpin_name[16].isdigit():
                #DEBUG print halpin_name
                i=int(halpin_name[16])
                xpos=float(self.hal['position_'+str(i)+'-pin33'])
                ypos=float(self.hal['torque_extremal_'+str(i)+'-pin33'])
                self.txt_items[i].setPos(xpos, ypos)
                self.txt_items[i].setText('%01d' % ypos)
                #self.w.plt33.clear()
                temp_data=self.plot_points.getData()
                temp_data[0][i]=xpos #FIXME здесь возникает ошибка
                temp_data[1][i]=ypos
                self.plot_points.setData(temp_data[0], temp_data[1])
                #self.plot_points.update()
                #self.w.plt33.update()
                #self.txt_items[i].setPos(xpos, ypos)???
        else:
            return

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

    def update_ini(self):
        # список на замену
        # replacelist = [[ur'^123'.encode(), ur'123'.encode()]]
        replacelist = [[ur"(NOM_DSP_IDLE\s*\=)\s*(\d+(.\d*){0,1})",
                        ur"\1 {:.1f}".format(self.w.spnDsp_Idle33.value())],
                       [ur"(NOM_VEL_IDLE\s*\=)\s*(\d+(.\d*){0,1})",
                        ur"\1 {:.1f}".format(self.w.spnVel_Idle33.value())],
                       [ur'(NOM_ACCEL_IDLE\s*\=)\s*(\d+(.\d*){0,1})',
                        ur"\1 {:.1f}".format(self.w.spnAccel_Idle33.value())],
                       [ur"(NOM_LOAD\s*\=)\s*(\d+(.\d*){0,1})",
                        ur"\1 {:.1f}".format(self.w.spnLoad33.value())],
                       [ur"(NOM_POS_MEASURE\s*\=)\s*(\d+(.\d*){0,1})",
                        ur"\1 {:.1f}".format(self.w.spnPos_Measure33.value())],
                       [ur"(NOM_DSP\s*_MEASURE\s*\=)\s*(\d+(.\d*){0,1})",
                        ur"\1 {:.1f}".format(self.w.spnDsp_Measure33.value())],
                       [ur"(NOM_VEL_MEASURE\s*\=)\s*(\d+(.\d*){0,1})",
                        ur"\1 {:.1f}".format(self.w.spnVel_Measure33.value())],
                       [ur"(NOM_ACCEL_MEASURE\s*\=)\s*(\d+(.\d*){0,1})",
                        ur"\1 {:.1f}".format(self.w.spnAccel_Measure33.value())]]

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
        #TODO обработка открыт/не открыт
        inilines = inifile2.writelines(inilines)
        inifile2.close()

    def convert_case(match_obj):
        if match_obj.group(1) is not None:
            return match_obj.group(1).lower()
        if match_obj.group(2) is not None:
            return match_obj.group(2).upper()


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
        #TODO дождаться записи файла и закрыть
        self.update_ini()
        event.accept()

################################
# required handler boiler code #
################################

def get_handlers(halcomp, widgets, paths):
     return [HandlerClass(halcomp, widgets, paths)]
