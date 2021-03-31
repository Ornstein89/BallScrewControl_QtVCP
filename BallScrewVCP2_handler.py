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
import sys, os, configparser, datetime, time, subprocess

# пакеты linuxcnc
import linuxcnc, hal # http://linuxcnc.org/docs/html/hal/halmodule.html

# пакеты GUI
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QFileDialog#, QHalLabel
from PyQt5.QtCore import Qt, QTime, QDateTime
from PyQt5.QtGui import QColor, QIcon

#from qtvcp.widgets import FocusOverlay, HALLabel
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

def timestamp():
    # https://gist.github.com/iverasp/9349dffa42aeffb32e48a0868edfa32d
    return int(time.mktime(datetime.datetime.now().timetuple()))


class TimeAxisItem(pg.AxisItem):
    # https://gist.github.com/iverasp/9349dffa42aeffb32e48a0868edfa32d
    def __init__(self, *args, **kwargs):
        super(TimeAxisItem, self).__init__(*args, **kwargs)
        #self.setLabel(text='Время', units='м:с')
        self.enableAutoSIPrefix(False)

    def tickStrings(self, values, scale, spacing):
        return [datetime.datetime.fromtimestamp(value).strftime("%M:%S") for value in values]

    #TODO возможно сюда как-то можно перенести проставление делений осей, чтобы сетка строилась по минутам и секундам

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
        self.RODOS_PATH = "/home/mdrives/RODOS4/RODOS4"
        self.gcodes = GCodes()
        self.plot_data_buffer = [[],[]]
        self.log_data_buffer = []
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
        self.start_log(self.datalogfileFILENAME)
        self.initialized = True
        # self.gcodes.setup_list() инструкция нужна только для отображения справочного списка команд
        #fov = FocusOverlay(self)
        #fov.show()

    def processed_key_event__(self,receiver,event,is_pressed,key,code,shift,cntrl):
        print "*** processed_key_event__: event.key() = ", event.key(), ", is_pressed = ", is_pressed
        if (event.key() == Qt.Key_Left) and self.w.btnStart_Ccw32.isEnabled():
            if is_pressed:
                self.w.btnStart_Ccw32.setChecked(True)
            else:
                self.w.btnStart_Ccw32.setChecked(False)
            #print '*** Qt.Key_Left'

        if (event.key() == Qt.Key_Right) and self.w.btnStart_Cw32.isEnabled():
            if is_pressed and (not self.w.btnStart_Cw32.isChecked()):
                print "*** 1"
                self.w.btnStart_Cw32.setChecked(True) #TODO вместо setChecked слот, имитирующий нажатие
                self.w.onbtnStart_Cw32_clicked(True)
                #self.w.btnStart_Cw32.pressed()
                #self.w.btnStart_Cw32.click()
                #self.w.btnStart_Cw32.animateClick()
#            elif (not is_pressed) and self.w.btnStart_Cw32.isChecked():
#                print "*** 2"
#                self.w.btnStart_Cw32.setChecked(False) #TODO вместо setChecked слот, имитирующий нажатие
#                self.w.onbtnStart_Cw32_clicked(False)
#                #self.w.btnStart_Cw32.released()
#                #self.w.btnStart_Cw32.click()
#                #self.w.btnStart_Cw32.animateClick()
#                #print '*** Qt.Key_Right'
        event.accept()
        return True

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

        # 16 марта 2021 - в ТЗ неточность, сигнал не нужен, привязка к BRAKE_TORQUE из формы 2.2
        #'torque_set-pin32': [None, self.onTorque_SetChanged], # пин связан с графиком, поэтому в отдельный слот для повышения производительности

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

        'RODOS4_1_on': [None, lambda s: self.onRODOS_changed(s,'RODOS4_1_on', 1, True)],
        'RODOS4_2_on': [None, lambda s: self.onRODOS_changed(s,'RODOS4_2_on', 2, True)],
        'RODOS4_3_on': [None, lambda s: self.onRODOS_changed(s,'RODOS4_3_on', 3, True)],
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
            self.VCP_halpins_float[key][0] = tmp_pin
            if self.VCP_halpins_float[key][1] is not None:
                tmp_pin.value_changed.connect(self.VCP_halpins_float[key][1])

            # создание пинов и связывание событий изменения HAL с обработчиком
        for key in self.VCP_halpins_bit:
            tmp_pin = self.hal.newpin(key, hal.HAL_BIT, hal.HAL_IN)
            self.VCP_halpins_bit[key][0] = tmp_pin
            if self.VCP_halpins_bit[key][1] is not None:
                tmp_pin.value_changed.connect(self.VCP_halpins_bit[key][1])

        STATUS.connect('state-on', self.on_state_on)
        STATUS.connect('state-off', self.on_state_off)

        return

#    def keyPressEvent(self, event):
#        if event.key() == Qt.Key_Left:
#            print '*** Qt.Key_Left'
#            return
#        if event.key() == Qt.Key_Right:
#            print '*** Qt.Key_Right'
#            return
#        return

    def on_state_on(self, data):
        print "*** on_state_on, data=", data
        pass

    def on_state_off(self, data):
        print "*** on_state_off, data=", data
        pass

    # # 16 марта 2021 - в ТЗ неточность, сигнал не нужен, привязка к BRAKE_TORQUE из формы 2.2
    # def onTorque_SetChanged(self, data):
    #     if not self.initialized:
    #         return
    #
    #     torque_set_value = self.hal['torque_set-pin32'] # * 0.1 + 1.0
    #     self.w.lblTorque_Set32.setText("{:10.1f}".format(torque_set_value))
    #     #self.hLine.setPos(pg.Point(torque_set_value, 0.0))
    #     self.hLine.setValue(torque_set_value)
    #     return

    def onTorque_ActualChanged(self, data):
        if not self.initialized:
            return

        if not self.TRIAL_IS_ON: # если  прожат stop - не отмечать точку на графике и не вести отсчёт времени
            return

         # если кнопки не зажаты - не отмечать точку на графике и не вести отсчёт времени
        if (not self.w.btnStart_Cw32.isChecked()) and (not self.w.btnStart_Ccw32.isChecked()):
            return

        # получить текущее время и отобразить его на label
        #DEBUG print "*** DATETIME_LAST = ", self.DATETIME_LAST
        tmpDateTime = QDateTime.currentDateTime()
        #DEBUG print "*** tmpDateTime = ", tmpDateTime
        delta_seconds = self.DATETIME0.msecsTo(tmpDateTime)/1000.0 - self.PAUSE_TIME_MS/1000.0 # время от начала испытания
        #DEBUG print "*** delta_seconds = ", delta_seconds
        if delta_seconds >= self.DURATION:
            self.onbtnStop32_clicked()

        self.w.lblTime_Current32.setText('%02d' % (delta_seconds // 60) + ':' + '%02d' % (delta_seconds % 60))

        # получить текущий момент и отобразить его на label
        torque_actual_value = self.hal['torque_actual-pin32'] # * 0.1 + 1.0
        self.w.lblTorque_Actual32.setText("{:10.1f}".format(torque_actual_value))
        #time_value = self.hal['time-pin32']# заменить на delta_seconds
        time_range = (self.w.tmedtTimeRange32.time().hour()*60*60 +
                      self.w.tmedtTimeRange32.time().minute()*60 +
                      self.w.tmedtTimeRange32.time().second()) # заменить на self.DURATION

        self.append_plot(delta_seconds, torque_actual_value)

        # оставить только точки в пределах [time_value-timerange, time_value]
        plotindex = 0
        while self.plot_data_buffer[0][plotindex] < (delta_seconds - time_range):
            plotindex += 1
        #plotindex += 1
        self.plot_data_buffer[0] = self.plot_data_buffer[0][plotindex:]
        self.plot_data_buffer[1] = self.plot_data_buffer[1][plotindex:]
        YMax = self.TORQUE_SET*1.2
        self.hLine.setValue(self.TORQUE_SET) #TODO ближайшие кратные 1, 2 и 5
        #TODO обновлять YMax если график улетает в космос

        self.update_plot() # обновить график
        #self.vLine.setPos(pg.Point(0.0, time_value))
        self.w.plt32.setXRange(delta_seconds - time_range, delta_seconds + time_range*0.1)

        # автомасштаб по Y
        self.w.plt32.setYRange(min([0.0, min(self.plot_data_buffer[1])]),
                               max([YMax, max(self.plot_data_buffer[1])]))
        self.w.plt32.clear() # обязательно очищать, иначе утечка памяти, объекты копятся на графике
        self.w.plt32.addItem(self.hLine, ignoreBounds=True, label='*Y')
        self.w.plt32.addItem(self.vLine, ignoreBounds=True, label='*X')
        self.w.plt32.plot(self.plot_data_buffer[0][:],
                          self.plot_data_buffer[1][:],
                          #clear = True,
                          pen = pg.mkPen(color=QColor(Qt.darkCyan), width=2))
        self.w.plt32.plot(self.plot_data_buffer[0][-1:],
                            self.plot_data_buffer[1][-1:],
                            #                  clear = True,
                            symbolPen = pg.mkPen(color=QColor(255,0,0,255), width=3),
                            symbol='o', symbolSize=10, symbolBrush=QColor(0,0,0,0),
                            label='{value:0.1f}',
                            labelOpts={'position':0.95, 'color': (255,0,0),
                                       'movable': False, 'fill': (0, 0, 200, 100)})
        self.vLine.setValue(delta_seconds)
        timedelta1 = datetime.timedelta(seconds=self.hal['time-pin32'])
        self.vLine.label.format = '%02d' % (delta_seconds // 60) + ':' + '%02d' % (delta_seconds % 60)
        self.w.lblTorque_Set32.setText("{:10.1f}".format(self.TORQUE_SET)) # сигнал torque_set выведен из исп. 16 марта, вместо него BRAKE_TORQUE
        self.hLine.setValue(self.TORQUE_SET)
        self.DATETIME_LAST = tmpDateTime
        #TODO плашка для VLine на графике

        return

    def onUpdateFloatSignals(self, data):
        halpin_name = self.w.sender().text()

        halpins_labels_match_precision1 = { # отображать с точностью 2 знака после запятой
        'geartorque_error_value-pin32':[self.w.lblGeartorque_Error_Value32, '%'],
        'geartorque_error_value_max32':[self.w.lblGeartorque_Error_Value_Max32, '%'],
        # убрали из ТЗ 22.03.2021 'braketorque_error_value-pin32':[self.w.lblBraketorque_Error_Value32, '%'],
        # убрали из ТЗ 22.03.2021 'braketorque_error_value_max32':[self.w.lblBraketorque_Error_Value_Max32, '%'],
        'load_error_value-pin32':[self.w.lblLoad_Error_Value32, ''],
        'load_error_value_max-pin32':[self.w.lblLoad_Error_Value_Max32, ''],
        'load_temperature-pin32':[self.w.lblLoad_Temperature32, ''],
        'load_temperature_max-pin32':[self.w.lblLoad_Temperature_Max32, ''],
        'pos_temperature-pin32':[self.w.lblPos_Temperature32, ''],
        'pos_temperature_max-pin32':[self.w.lblPos_Temperature_Max32, '']
        }

        if(halpin_name in halpins_labels_match_precision1):
            halpin_value = self.hal[halpin_name]
            halpins_labels_match_precision1[halpin_name][0].setText("{:10.1f}".format(halpin_value)
                +halpins_labels_match_precision1[halpin_name][1])

        #if(halpin_name == 'time-pin32'): #TODO заменить на 'time_current-pin32'
        #    timedelta1 = datetime.timedelta(seconds=self.hal['time-pin32']) #TODO заменить на 'time_current-pin32'
        #    self.w.lblTime_Current32.setText('%02d' % (timedelta1.seconds // 60) + ':' + '%02d' % (timedelta1.seconds % 60))
            #TODO перевести на сигнал duration
            # timedelta2 = datetime.timedelta(seconds=self.hal['duration-pin32'])
            # self.w.lblDuration32.setText('%02d'%(timedelta2.seconds // 60) + ':' + '%02d'%(timedelta2.seconds % 60))


        return

    def onTimeChanged(self, data):
        #TODO
        if not self.initialized:
            return

        self.current_time = self.hal['time-pin32']
        pass

    def onAppend_BufferChanged(self, data):
        # запись показаний производится в буфер для повышения производительности
        # TODO улучшить менеджмент памяти - выделять блоками (либо за этим следит интерпретатор питона)
        # TODO ограничение на длину???
        # Вектор параметров состояния: (time_current; torque_actual; omega_actual)
        # self.log_data_buffer.append([self.current_time, self.current_position]) # значения без лишнего обращения к пинам, для улучшения производительности
        if not self.initialized:
            return

        # только восходящий фронт
        if not self.hal['append_buffer-pin32']:
            return

        self.log_data_buffer.append([self.hal['time-pin32'], #TODO 'time_current-pin32'
            self.hal['torque_actual-pin32'],
            self.hal['omega_actual-pin32']]) # получение значений с hal-пинов, может снижать производительность

        # форма 3.3, Вектор параметров состояния: (time; pos_measure; load; torque_at_load; torque_extremal)
        # self.log_data_buffer.append([time, pos_measure, load, torque_at_load, torque_extremal])
        # форма 3.4
        pass

    def onAppend_TitleChanged(self, data):
        if not self.hal['append_title-pin32']:
            return
        # только восходящий фронт
        if not self.initialized:
            return

        self.datalogfile.write('\n')
        self.datalogfile.write('Время запуска:\t' + str(datetime.timedelta(seconds=self.hal['time-pin32'])) + '\n')
        self.datalogfile.write('Направление:\t' + str(self.hal['dir-pin32']) + '\n')
        self.datalogfile.write('\n')
        self.datalogfile.write('Время работы\tКрутящий момент\tСкорость вращения\n')
        self.datalogfile.flush()
        return

    def onAppend_FileChanged(self, data):
        # Вектор параметров состояния: (time_current; torque_actual; omega_actual)
        if not self.hal['append_file-pin32']:
            return
        if not self.initialized:
            return
        for rec in self.log_data_buffer:
            # время
            str_to_print = str(datetime.timedelta(seconds=rec[0])) + '\t'
            # torque_actual
            str_to_print += "{:.1f}".format(rec[1]) + '\t'
            # omega_actual
            str_to_print += "{:.1f}".format(rec[2]) + '\n'
            self.datalogfile.write(str_to_print)
        self.datalogfile.flush()
        self.log_data_buffer = []
        return

    def onbtnStart_Ccw32_clicked(self, state):
        if state:
            self.w.btnStart_Cw32.setChecked(False)
            self.w.btnStart_Cw32.setEnabled(False)

        #if self.w.btnStart_Ccw32.isChecked():
        #    self.w.btnStart_Cw32.setChecked(False)
        #if self.w.btnStart_Ccw32.isChecked():
        #    self.w.btnStart_Cw32.setEnabled(False)
        if state and (not self.TRIAL_IS_ON): # первое нажатие после Stop
            self.DATETIME0 = QDateTime.currentDateTime() # системное время начала цикла испытаний
            self.DATETIME_LAST = QDateTime.currentDateTime() #
            self.PAUSE_TIME_MS = 0.0 # кол-во миллисекунд, которые испытания пробыли в паузе
            self.w.plt32.clear()
            self.plot_data_buffer = [[],[]]
        if state and self.TRIAL_IS_ON: # если включение после паузы
            pause_add_ms = self.DATETIME_LAST.msecsTo(QDateTime.currentDateTime())
            print "*** pause_add_ms = ", pause_add_ms
            self.PAUSE_TIME_MS = self.PAUSE_TIME_MS + pause_add_ms
            print "*** self.PAUSE_TIME_MS = ", self.PAUSE_TIME_MS
        self.TRIAL_IS_ON = True

    def onbtnStart_Cw32_clicked(self, state):
        if state:
            self.w.btnStart_Ccw32.setChecked(False)
            self.w.btnStart_Ccw32.setEnabled(False)
            #if self.w.btnStart_Cw32.isChecked():
            #    self.w.btnStart_Ccw32.setChecked(False)
            #if self.w.btnStart_Cw32.isChecked():
            #    self.w.btnStart_Ccw32.setEnabled(False)
        if state and (not self.TRIAL_IS_ON):  # если включение из положения stop
            self.DATETIME0 = QDateTime.currentDateTime()# системное время начала цикла испытаний
            self.DATETIME_LAST = QDateTime.currentDateTime()
            self.PAUSE_TIME_MS = 0.0 # кол-во миллисекунд, которые испытания пробыли в паузе
            self.w.plt32.clear()
            self.plot_data_buffer = [[],[]]
        if state and self.TRIAL_IS_ON: # если включение после паузы
            pause_add_ms = self.DATETIME_LAST.msecsTo(QDateTime.currentDateTime())
            print "*** pause_add_ms = ", pause_add_ms
            self.PAUSE_TIME_MS = self.PAUSE_TIME_MS + pause_add_ms
            print "*** self.PAUSE_TIME_MS = ", self.PAUSE_TIME_MS
        self.TRIAL_IS_ON = True

    def onbtnStop32_clicked(self):
        self.w.btnStart_Cw32.setChecked(False)
        self.w.btnStart_Cw32.setEnabled(STATUS.machine_is_on())
        self.w.btnStart_Ccw32.setChecked(False)
        self.w.btnStart_Ccw32.setEnabled(STATUS.machine_is_on())
        #self.DATETIME0 = QDateTime.currentDateTime(),
        #self.DATETIME_LAST = QDateTime.currentDateTime(),
        self.TRIAL_IS_ON = False

    def onRODOS_changed(self, state, pinname, number, turn_on):
        #INFO http://linuxcnc.org/docs/2.8/html/gui/qtvcp_code_snippets.html#_add_hal_pins_that_call_functions
        print "*** onRODOS_changed() : pinname=",pinname, ", number=", number, ", turn_on=", turn_on
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

    def closeEvent(self, event):

        # оверлей с запросом на выключение
        self.w.overlay.text='Выключить?'
        #self.w.overlay.bg_color = QtGui.QColor(0, 0, 0, 150)
        self.w.overlay.resize(self.w.size())
        self.w.overlay.show()
        self.w.overlay.update()

        #if self.shutdown_check:
        answer = MSG.showdialog('Выключить приложение?',
            details='',
            display_type='YESNO')
        if not answer:
            self.w.overlay.hide()
            event.ignore()
            return

        self.w.overlay.text='Закрытие файлов и выключение'

        # дождаться записи файла и закрыть
        self.datalogfile.flush()
        self.datalogfile.close()
        print "*** closeEvent"
        event.accept()


    def onDirChanged(self, data):
        pass

    def onBtnDeviceOff(self):
        #ACTION.SET_MACHINE_STATE(linuxcnc.STATE_OFF)
        ACTION.SET_MACHINE_STATE(False)

    #####################
    # GENERAL FUNCTIONS #
    #####################

    def init_gui(self):
        self.w.setWindowIcon(QIcon("BallScrewControlIcon.png"))
        self.DATETIME0 = QDateTime.currentDateTime()
        self.DATETIME_LAST = QDateTime.currentDateTime()
        self.PAUSE_TIME_MS = 0.0
        self.TRIAL_IS_ON = False
        self.load_ini()
        self.init_led_colors()

        # STATUS.connect('state-on', lambda w: self.w.btnDevice_On32.setEnabled(False))
        # STATUS.connect('state-on', lambda w: self.w.btnDevice_Off32.setEnabled(True))
        # STATUS.connect('state-off', lambda w: self.w.btnDevice_On32.setEnabled(True))
        # STATUS.connect('state-off', lambda w: self.w.btnDevice_Off32.setEnabled(False))
        # STATUS.connect('state-estop-reset', lambda w: self.w.btnDevice_Off32.setEnabled(False))

        #TODO связать с action-сигналом
        STATUS.connect('state-estop',
                        lambda w: (self.w.btnDevice_On32.setEnabled(False)))
        STATUS.connect('state-estop-reset',
                        lambda w: (self.w.btnDevice_On32.setEnabled(not STATUS.machine_is_on())))


        self.w.btnDevice_On32.clicked.connect(lambda x: ACTION.SET_MACHINE_STATE(True))

        STATUS.connect('state-on', lambda _: (self.w.btnStart_Ccw32.setEnabled(True),
                                              self.w.btnStop32.setEnabled(True),
                                              self.w.btnStart_Cw32.setEnabled(True),
                                              self.w.btnDevice_On32.setEnabled(False)))

        STATUS.connect('state-off', lambda _:(self.onbtnStop32_clicked(),
                                              self.w.btnStart_Ccw32.setEnabled(False),
                                              self.w.btnStop32.setEnabled(False),
                                              self.w.btnStart_Cw32.setEnabled(False),
                                              self.w.btnDevice_On32.setEnabled(STATUS.estop_is_clear()) ))

        self.w.btnStart_Ccw32.clicked.connect(self.onbtnStart_Ccw32_clicked)

        self.w.btnStart_Cw32.clicked.connect(self.onbtnStart_Cw32_clicked)

        self.w.btnStop32.clicked.connect(self.onbtnStop32_clicked)
        self.w.lblDuration32.setText(QTime(0,0,0).addSecs(self.DURATION).toString("mm:ss"))
        #STATUS.connect('state-estop-reset', lambda w: self._flip_state(False))
        #self.w.lblTest = QHalLabel()
        #self.w.lblTest.setText("!!!HAL Label!!!")
        # self.w.gridLayout_29.addWidget(self.w.lblTest, 3, 2)
        self.init_plot()

        # создать оверлей для диалого завершения
        self.w.overlay = FocusOverlay(self.w)
        self.w.overlay.setGeometry(self.w.geometry())
        self.w.overlay.hide()
        return

    def resizeEvent(self, event):
        print "*** resizeEvent(), newSize"
        self.w.overlay.resize(self.w.size())
        event.accept()

    def init_led_colors(self):
        # настройка цветов диодов (т.к. в дизайнере цвета выставляются с ошибками - одинаковый цвет для color и off_color)

        diodes_redgreen = ( # набор LED, для которых надо установить красный/зелёный цвета
            self.w.ledGeartorque_Error32,#.setOffColor(Qt.red)
            self.w.ledGeartorque_Error32,#.setColor(Qt.green)
            # убрали из ТЗ 22.03.2021  self.w.ledBraketorque_Error32,
            self.w.ledEstop_Ext32,
            # убрали из ТЗ 22.03.2021 self.w.ledLoad_Is_On2_32,
            self.w.ledLoad_Alarm32,
            self.w.ledLoad_Error32,
            self.w.ledLoad_Overheat32,
            # убрали из ТЗ 22.03.2021 self.w.ledPos_Is_On_2_32,
            self.w.ledPos_Alarm32,
            self.w.ledPos_Overheat32)

        diodes_greenred = (  # инверсия
            self.w.ledIs_Running_Cw32,
            self.w.ledIs_Running_Ccw32,
            self.w.ledEnable32)

        for led in diodes_redgreen:
            led.setColor(Qt.red)
            led.setOffColor(Qt.green)

        for led in diodes_greenred: # инверсия
            led.setColor(Qt.green)
            led.setOffColor(Qt.red)

    def init_plot(self):
        self.w.plt32.setBackground('w')
        styles = {'color':'r', 'font-size':'20px'}
        self.w.plt32.setLabel('left', 'T [Н*м]', **styles)
        self.w.plt32.setLabel('bottom', 'Время', **styles)

        font=QtGui.QFont()
        font.setPixelSize(20)
        self.hLine = pg.InfiniteLine(angle=0, movable=False,
            pen=pg.mkPen(color=QColor(Qt.blue),
            width = 2, style=Qt.DashDotLine),
            label='{value:0.1f}',
            labelOpts={'position':0.95, 'color': (255,0,0),
                       'movable': False, 'fill': (0, 0, 200, 100)})
        #self.hLine.setPos(pg.Point(0.0, 10.0))
        YMax = self.TORQUE_SET*1.2
        self.hLine.setValue(self.TORQUE_SET) #TODO ближайшие кратные 1, 2 и 5
        self.hLine.setZValue(1)
        self.w.plt32.setYRange(0.0, YMax)
        #self.w.plt32.enableAutoRange(axis = "y", enable = True)
        self.w.plt32.addItem(self.hLine, ignoreBounds=True)

        self.vLine = pg.InfiniteLine(angle=90, movable=False,
            pen=pg.mkPen(color=QColor(Qt.blue),
            width = 2, style=Qt.DashDotLine),
            label='00:00:00',
            labelOpts={'position':0.95, 'color': (255,0,0),
                       'movable': False, 'fill': (0, 0, 200, 100)})
        #self.vLine.setPos(pg.Point(1.0, 0.0))
        self.vLine.setValue(0.5)
        self.vLine.setZValue(1)
        self.w.plt32.addItem(self.vLine, ignoreBounds=True)

        font=QtGui.QFont()
        font.setPixelSize(20)
        #plot.getAxis("bottom").tickFont = font
        # https://gist.github.com/iverasp/9349dffa42aeffb32e48a0868edfa32d
        self.w.plt32.setAxisItems({'bottom': TimeAxisItem(orientation='bottom')})
        self.w.plt32.getAxis("bottom").setStyle(tickFont = font)
        self.w.plt32.getAxis("left").setStyle(tickFont = font)

        # деления на оси X чтобы по ним строилась сетка
        self.w.plt32.showGrid(x = True, y = True, alpha = 1.0)
        self.w.plt32.getAxis('bottom').setTickSpacing(major=60, minor=1) # деления на оси X чтобы по ним строилась сетка
        self.w.plt32.getAxis('bottom').setGrid(255)
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
            #'torque_set-pin32':self.w.lblTorque_Set32, # сигнал torque_set выведен из исп. 16 марта, вместо него BRAKE_TORQUE
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
        self.plot_data_buffer[0].append(x)
        self.plot_data_buffer[1].append(y)
        #
        # self.plot_data_buffer[0][self.current_plot_n] = x
        # self.plot_data_buffer[1][self.current_plot_n] = y
        # self.current_plot_n += 1
        # if(self.current_plot_n >= 10000):
        #     self.current_plot_n = 0 # логика кольцевого буфера
        # return

    def update_plot(self):
        if(self.current_plot_n < 20):
            #print "*** plot < 20"
            self.w.plt32.plot(self.plot_data_buffer[0][0:self.current_plot_n],
                              self.plot_data_buffer[1][0:self.current_plot_n],
                              clear = True)
        else:
            #print "*** plot >= 20"
            self.w.plt32.plot(self.plot_data_buffer[0][self.current_plot_n-20:self.current_plot_n],
                              self.plot_data_buffer[1][self.current_plot_n-20:self.current_plot_n],
                              clear=True)
        return

    def on_siggen_test_read_pin_value_changed(self, data):
        return
        #print("*** siggen pin data: ", data)
        #print("*** siggen pin: ", self.siggen_test_read_pin.get())
        #print("*** siggen.0.sine directly", hal.get_value("siggen.0.sine"))

    def start_log(self, logfilename):
        self.datalogfile = None
        self.datalogfile = open(logfilename,"w")
        self.datalogfile.write("Модель: " + self.MODEL + '\n')
        self.datalogfile.write("Номер изделия: " + self.PART + '\n')
        self.datalogfile.write("Дата: " + self.DATE + '\n')
        self.datalogfile.write('\n')
        self.datalogfile.flush()

    #TODO в принципе функция не нужна, т.к. linuxcnc сам поддерживает передачу параметров из ini
    def load_ini(self):
        #self.TYPE = INFO.INI.findall("BALLSCREWPARAMS", "TYPE")[0]
        #print "*** self.TYPE = ", self.TYPE
        self.TYPE = INFO.INI.findall("BALLSCREWPARAMS", "TYPE")[0]
        self.datalogfileFILENAME = INFO.INI.findall("BALLSCREWPARAMS", "LOGFILE")[0]
        self.MODEL = INFO.INI.findall("BALLSCREWPARAMS", "MODEL")[0]
        self.BRAKE_TORQUE = float(INFO.INI.findall("BALLSCREWPARAMS", "BRAKE_TORQUE")[0])
        self.GEAR = float(INFO.INI.findall("BALLSCREWPARAMS", "GEAR")[0])
        self.EFFICIENCY = float(INFO.INI.findall("BALLSCREWPARAMS", "EFFICIENCY")[0])
        self.TORQUE_SET = self.BRAKE_TORQUE / (self.GEAR * self.EFFICIENCY)
        self.DURATION = int(INFO.INI.findall("BALLSCREWPARAMS", "DURATION")[0])
        self.DATE = INFO.INI.findall("BALLSCREWPARAMS", "DATE")[0]
        self.PART = INFO.INI.findall("BALLSCREWPARAMS", "PART")[0]
        #self.datalogfile.write("Номе изделия: " + self.PART + "\n")
        #self.datalogfile.write("Дата: " + self.DATE + "\n")
        #TODO обработка ошибок и исключений: 1) нет файла - сообщение и заполнение по умолчанию, создание конфига
        #TODO обработка ошибок и исключений: 2) нет ключей в конфиге - сообщение и заполнение по умолчанию
    
################################
# required handler boiler code #
################################

def get_handlers(halcomp, widgets, paths):
     return [HandlerClass(halcomp, widgets, paths)]
