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
import sys, os, configparser, subprocess

# пакеты linuxcnc
import linuxcnc, hal # http://linuxcnc.org/docs/html/hal/halmodule.html

# пакеты GUI
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import Qt

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
ACTION = Action() # http://linuxcnc.org/docs/2.8/html/gui/qtvcp_libraries.html#_action
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
    def __init__(self, halcomp, widgets, paths):
        self.hal = halcomp
        self.PATHS = paths
        #self.gcodes = GCodes()
        self.data = [[None for _ in range(10000)],[None for _ in range(10000)]]
        self.current_plot_n = 0
        self.w = widgets
        self.RODOS_PATH = "/home/mdrives/RODOS4/RODOS4"
        self.position_buffer = []
        self.load_ini()
        self.start_log()
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

        # self.gcodes.setup_list() инструкция нужна только для отображения справочного списка команд

    def processed_key_event__(self,receiver,event,is_pressed,key,code,shift,cntrl):
        if event.key() == Qt.Key_Left and self.w.btnJog_Minus31.isEnabled():
            if is_pressed and not self.w.btnJog_Minus31.isDown():
                self.w.btnJog_Minus31.setDown(True)
                #self.w.btnJog_Minus31.click(True)
                self.w.btnJog_Minus31.pressed.emit()
                #self.w.btnJog_Minus31.setCheckable(True)
                #self.w.btnJog_Minus31.setChecked(True)
            elif self.w.btnJog_Minus31.isDown():
                self.w.btnJog_Minus31.setDown(False)
                #self.w.btnJog_Minus31.click(False)
                self.w.btnJog_Minus31.released.emit()
                #self.w.btnJog_Minus31.setChecked(False)
                #self.w.btnJog_Minus31.setCheckable(False)
            #print '*** Qt.Key_Left'
            # event.accept()

        if event.key() == Qt.Key_Right and self.w.btnJog_Plus31.isEnabled():
            if is_pressed and not self.w.btnJog_Plus31.isDown():
                self.w.btnJog_Plus31.setDown(True)
                self.w.btnJog_Plus31.pressed.emit()
                # self.w.btnJog_Plus31.click(True)
                # self.w.btnJog_Plus31.press()
                # self.w.btnJog_Plus31.setCheckable(True)
                # self.w.btnJog_Plus31.setChecked(True)
            elif self.w.btnJog_Plus31.isDown():
                self.w.btnJog_Plus31.setDown(False)
                self.w.btnJog_Plus31.released.emit()
                # self.w.btnJog_Plus31.click(True)
                # self.w.btnJog_Plus31.release()
                # self.w.btnJog_Plus31.setChecked(False)
                # self.w.btnJog_Plus31.setCheckable(False)

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
        #TODO дождаться записи файла и закрыть
        event.accept()
        print '*** closeEvent'

    ########################
    # CALLBACKS FROM STATUS#
    ########################

    #######################
    # CALLBACKS FROM FORM #
    #######################
    def init_pins(self):
        # создание HAL-пинов приложения
        self.VCP_halpins_float = {
            'position-pin31': [None, self.onPositionChanged],
            'position_actual-pin31': [None, self.onPosition_ActualChanged],
            'time-pin31':[None, self.onTimeChanged]
        }

        self.VCP_halpins_bit = {
            'active_0-pin':[None, self.onActive0Changed],
            'append_buffer-pin31': [None, self.onAppend_BufferChanged],
            'append_file-pin31': [None, self.onAppend_FileChanged],

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

        # создание числовых пинов и связывание событий изменения HAL с обработчиком
        for key in self.VCP_halpins_float:
            tmpPin = self.hal.newpin(key, hal.HAL_FLOAT, hal.HAL_IN)
            self.VCP_halpins_float[key][0] = tmpPin # получить ссылку чтобы не обращаться через словарь
            if self.VCP_halpins_float[key][1] is not None: # если не None - назначить обработчик
                tmpPin.value_changed.connect(self.VCP_halpins_float[key][1])

        # создание битовых пинов и связывание событий изменения HAL с обработчиком
        for key in self.VCP_halpins_bit:
            tmpPin = self.hal.newpin(key, hal.HAL_BIT, hal.HAL_IN)
            self.VCP_halpins_bit[key][0] = tmpPin # получить ссылку чтобы не обращаться через словарь
            if self.VCP_halpins_bit[key][1] is not None: # если не None - назначить обработчик
                tmpPin.value_changed.connect(self.VCP_halpins_bit[key][1])

        # try:
        #     #p = subprocess.Popen(["sh","-c",name_file]) # записывает в файл
        #     return_code = subprocess.call("sudo /home/mdrives/RODOS4/./RODOS4 -a --c3 128", shell=False)
        #     print "*** subprocess.call() returns ", return_code
        #     return_code = subprocess.call("sudo /home/mdrives/RODOS4/./RODOS4 -a --c4 128", shell=False)
        #     print "*** subprocess.call() returns ", return_code
        # except Exception as exc:
        #     print "***Ошибка при запуске RODOS4. ", exc

        return

    def onBtnSaveState31(self):
        #TODO
        pass

    def onBtnOn31(self):
        #INFO https://github.com/LinuxCNC/linuxcnc/blob/master/share/qtvcp/screens/qt_cnc_800x600/qt_cnc_800x600_handler.py
        # ACTION.SET_MACHINE_STATE(not STATUS.machine_is_on())

        #INFO http://linuxcnc.org/docs/2.8/html/gui/qtvcp_custom_widgets.html#_custom_hal_widgets
        # STATUS.connect('state-on', lambda w:self._flip_state(True))

        if not STATUS.machine_is_on():
            ACTION.SET_MACHINE_STATE(True) #INFO http://linuxcnc.org/docs/2.8/html/gui/qtvcp_libraries.html#_action
            #DEBUG dir_path = os.path.dirname(os.path.realpath(__file__))
            #DEBUG print "*** dir_path = ", dir_path
            #DEBUG print "*** os.getcwd() = ", os.getcwd()
        return

    def runRODOS_31(self):
        pass
        #try:
        #    #DEBUG p = subprocess.Popen(["sh","-c",name_file]) # записывает в файл
        #    #DEBUG return_code = subprocess.call(["pwd"], shell=True)
        #    #DEBUG return_code = subprocess.call(["sudo ls"], shell=True)
        #    #DEBUG print "*** subprocess.call([\"sudo\", \"ls\"]) returns ", return_code
        #    return_code = subprocess.call("sudo /home/mdrives/RODOS4/RODOS4 -a --c3 128", shell=True)
        #    print "*** subprocess.call() returns ", return_code
        #    return_code = subprocess.call("sudo /home/mdrives/RODOS4/RODOS4 -a --c4 128", shell=True)
        #    print "*** subprocess.call() returns ", return_code
        #except Exception as exc:
        #    print "***Ошибка при запуске RODOS4. ", exc

    def stopRODOS_31(self):
        pass
        #try:
        #    #DEBUG p = subprocess.Popen(["sh","-c",name_file]) # записывает в файл
        #    #DEBUG return_code = subprocess.call(["pwd"], shell=True)
        #    #DEBUG return_code = subprocess.call(["sudo ls"], shell=True)
        #    #DEBUG print "*** subprocess.call([\"sudo\", \"ls\"]) returns ", return_code
        #    return_code = subprocess.call("sudo /home/mdrives/RODOS4/RODOS4 -a --c3 0", shell=True)
        #    print "*** subprocess.call() returns ", return_code
        #    return_code = subprocess.call("sudo /home/mdrives/RODOS4/RODOS4 -a --c4 0", shell=True)
        #    print "*** subprocess.call() returns ", return_code
        #except Exception as exc:
        #    print "***Ошибка при запуске RODOS4. ", exc

    def onBtnOff31(self):
        #try:
        #    #INFO run  - рекомендован по сравнению с call, но его нет в Python 2
        #    #INFO Popen - неблокирующий
        #    #INFO call - обёртка над Popen + wait (блокирующий), call = ACTIONrun(...).returncode
        #
        #    #p = subprocess.Popen(["sh","-c",name_file]) # записывает в файл
        #    return_code = subprocess.call("sudo /home/mdrives/RODOS4/./RODOS4 -a --c3 0", shell=False)
        #    print "*** subprocess.call() returns ", return_code
        #    return_code = subprocess.call("sudo /home/mdrives/RODOS4/./RODOS4 -a --c4 0", shell=False)
        #    print "*** subprocess.call() returns ", return_code
        #except Exception as exc:
        #    print "***Ошибка при запуске RODOS4. ", exc
        ACTION.SET_MACHINE_STATE(False)
        # self.w.btnDevice_On31.setChecked(False)

    def keyPressEvent(self, event):
        #TODO
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
        diodes_redgreen = ( self.w.ledPos_Alarm31, )

        for led in diodes_redgreen:
            led.setColor(Qt.green)
            led.setOffColor(Qt.green)
        ini_control_match_dict = {
            'NOM_VEL' : (self.w.sldVelocity31, self.w.spnVelocity31),
            'NOM_ACCEL' : (self.w.sldAcceleration31, self.w.spnAcceleration31)
        }


        for key, controls in ini_control_match_dict.items():
            print '***controls[0] = ', controls[0]
            print '***controls[1] = ', controls[1]
            controls[0].setMinimum(int(float(INFO.INI.findall("BALLSCREWPARAMS", key+'_MIN')[0])*100))
            controls[0].setMaximum(int(float(INFO.INI.findall("BALLSCREWPARAMS", key+'_MAX')[0])*100))
            controls[0].setValue(int(float(INFO.INI.findall("BALLSCREWPARAMS", key)[0])*100))
            controls[1].setMinimum(float(INFO.INI.findall("BALLSCREWPARAMS", key+'_MIN')[0]))
            controls[1].setMaximum(float(INFO.INI.findall("BALLSCREWPARAMS", key+'_MAX')[0]))
            controls[1].setValue(float(INFO.INI.findall("BALLSCREWPARAMS", key)[0]))

        self.w.sldVelocity31.valueChanged.connect(lambda val: self.w.spnVelocity31.setValue(float(val)/100.0))
        self.w.spnVelocity31.valueChanged.connect(lambda val: self.w.sldVelocity31.setValue(int(val*100)))
        self.w.sldAcceleration31.valueChanged.connect(lambda val: self.w.spnAcceleration31.setValue(float(val)/100.0))
        self.w.spnAcceleration31.valueChanged.connect(lambda val: self.w.sldAcceleration31.setValue(int(val*100)))

        STATUS.connect('state-estop', lambda w: (self.w.btnDevice_On31.setEnabled(False)))
        STATUS.connect('state-estop-reset', lambda w: (self.w.btnDevice_On31.setEnabled(not STATUS.machine_is_on())))

        STATUS.connect('state-on', lambda s: (self.w.btnJog_Minus31.setEnabled(self.w.chkActivation31.isChecked()),
                                              self.w.btnJog_Plus31.setEnabled(self.w.chkActivation31.isChecked()),
                                              self.w.btnLog_Trigger31.setEnabled(True),
                                              self.w.btnDevice_On31.setEnabled(False),
                                              self.w.chkActivation31.setEnabled(True)))

        STATUS.connect('state-off', lambda s:(self.w.btnJog_Minus31.setEnabled(False),
                                              self.w.btnJog_Plus31.setEnabled(False),
                                              self.w.btnLog_Trigger31.setEnabled(False),
                                              self.w.btnDevice_On31.setEnabled(STATUS.estop_is_clear()),
                                              self.w.chkActivation31.setEnabled(False)))

        self.w.chkActivation31.stateChanged.connect(
            lambda s:(self.w.btnJog_Minus31.setEnabled(STATUS.machine_is_on()
                        and self.w.chkActivation31.isChecked()),
                      self.w.btnJog_Plus31.setEnabled(STATUS.machine_is_on()
                        and self.w.chkActivation31.isChecked())))
        self.w.ledPos_Alarm31.setOffColor(Qt.yellow)
        # add overlay to topWidget
        self.w.overlay = FocusOverlay(self.w)
        self.w.overlay.setGeometry(0, 0, self.w.width(), self.w.height())
        self.w.overlay.hide()
        return

    # def resizeEvent(self, event):
    #     print "*** resizeEvent(), newSize"
    #     self.w.overlay.resize(self.w.size())
    #     event.accept()

    def onPositionChanged(self, data):
        halpin_value = self.hal['position-pin31']
        self.w.lblPosition31.setText("{:10.2f}".format(halpin_value))
        pass

    def onBtnTest(self, data):
        ### Тестирование правильной отрисовки оверлея
        self.w.overlay.text='Выключить?'
#        self.w.overlay.bg_color = QtGui.QColor(0, 0, 0,150)
        self.w.overlay.resize(self.w.size())
        self.w.overlay.show()
        self.w.overlay.update() # !!!!!!!! именно этой строчки не хватало
#        self.w.overlay.setVisible(not self.w.overlay.isVisible())

        answer = MSG.showdialog('Do you want to shutdown now?',
            details='You can set a preference to not see this message',
            display_type='YESNO')
        if not answer:
            self.w.overlay.hide()
#            event.ignore()
            return

        ### Тестирование ...
        return

    def onPosition_ActualChanged(self, data):
        halpin_value = self.hal['position_actual-pin31']
        #print '*** onPosition_ActualChanged, data=', data
        self.w.lblPosition_Actual31.setText("{:10.2f}".format(halpin_value))
        self.current_position = self.hal['position_actual-pin31']
        pass

    def onActive0Changed(self, data):
        if not STATUS.machine_is_on():
            return
        self.w.sldVelocity31.setEnabled(self.hal['active_0-pin'])
        self.w.sldAcceleration31.setEnabled(self.hal['active_0-pin'])
        self.w.spnVelocity31.setEnabled(self.hal['active_0-pin'])
        self.w.spnAcceleration31.setEnabled(self.hal['active_0-pin'])

    def onTimeChanged(self, data):
        #TODO
        self.current_time = self.hal['time-pin31']
        pass

    def onAppend_BufferChanged(self, data):
        # запись показаний производится в буфер для повышения производительности
        #TODO улучшить менеджмент памяти - выделять блоками (либо за этим следит интерпретатор питона)
        #TODO ограничение на длину???
        if not self.hal['append_buffer-pin31']: # исключить обратный фронт сигнала
            return
        self.position_buffer.append([self.current_time, self.current_position]) # значения без лишнего обращения к пинам, для улучшения производительности
        # self.position_buffer.append([self.hal['position_actual-pin31'], self.hal['time-pin31']]) # получение значений с hal-пинов, может снижать производительность

        # форма 3.3, Вектор параметров состояния: (time; pos_measure; load; torque_at_load; torque_extremal)
        # self.position_buffer.append([time, pos_measure, load, torque_at_load, torque_extremal])
        # форма 3.4
        pass

    def onAppend_FileChanged(self, data):
        if not self.hal['append_file-pin31']: # исключить обратный фронт сигнала
            return
        #записать показания в файл
        for rec in self.position_buffer:
            self.logfile.write('Фактический ход:\t' + str(rec[0]))
            self.logfile.write('Время:\t' + str(rec[1]))
            self.logfile.write('\n')
        # форма 3.2 Вектор параметров состояния: (time_current; torque_actual; omega_actual)

        # форма 3.3, Вектор параметров состояния: (time; pos_measure; load; torque_at_load; torque_extremal)
        # for rec in self.position_buffer:
        #     self.logfile.write('Время измерения:\t'  time)
        #     self.logfile.write('Положение измерения:\t'  pos_measure)
        #     self.logfile.write('Нагрузка:\t'  load)
        #     self.logfile.write('Приведённый момент от нагрузки:\t'  torque_at_load)
        #     self.logfile.write('Момент страгивания:\t'  torque_extremal)
        #     self.logfile.write('\n')

        # форма 3.4 Вектор параметров состояния: (time_current; position_actual; omega_actual; load_actual; torque_actual)
        #TODO
        self.position_buffer = [] # очистить буфер после записи
        pass

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


    #def pinCnagedCallback(self, data):
    #    """
    #    Один общий слот под все сигналы - снижает производительность
    #    """
    #    halpin_name = self.w.sender().text()
    #
    #    # отдельные пины, отвечающий за активность графических компонентов
    #    if(halpin_name == 'active_0-pin'):
    #        self.w.sldVelocity31.setEnabled(self.hal['active_0-pin'])
    #        self.w.sldAcceleration31.setEnabled(self.hal['active_0-pin'])
    #        return
    #
    #    # соответствие пинов float и табличек, на которых нужно отображать значение
    #    halpins_labels_match_precision2 = { # отображать с точностью 2 знака после запятой
    #        'position-pin31':self.w.lblPosition31,
    #        'position_actual-pin31':self.w.lblPosition_Actual31,
    #        }
    #
    #    if(halpin_name in halpins_labels_match_precision2):
    #        halpin_value = self.hal[halpin_name]
    #        halpins_labels_match_precision2[halpin_name].setText("{:10.2f}".format(halpin_value))
    #
    #    return
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

    def start_log(self):
        self.logfile = open(self.LOGFILE, 'w')
        #Заголовок лога
        self.logfile.write('Модель:\t' + self.MODEL + '\n')
        self.logfile.write('Номер изделия: ' + self.PART + '\n')
        self.logfile.write('Дата: ' + self.DATE + '\n')
        self.logfile.write('\n')

        self.logfile.write('Проектный ход: ' + self.TRAVEL + '\n')

        #if False: # форма 3.2
        #     self.logfile.write('Нагрузка:\t', self.BRAKE_TORQUE)
        #     self.logfile.write('Частота вращения:\t', self.NOM_VEL)
        #if False: # форма 3.3
        #    self.logfile.write('Нагрузка:\t', self.BRAKE_TORQUE)
        #    self.logfile.write('Частота вращения:\t', self.NOM_VEL)
        #if False:  # форма 3.4
        #    self.logfile.write('Количество циклов:\t', self.N)

        self.logfile.write('\n')
        return

    def on_siggen_test_read_pin_value_changed(self, data):
        return
        #print("*** siggen pin data: ", data)
        #print("*** siggen pin: ", self.siggen_test_read_pin.get())
        #print("*** siggen.0.sine directly", hal.get_value("siggen.0.sine"))

    #TODO в принципе функция не нужна, т.к. linuxcnc сам поддерживает передачу параметров из ini
    def load_ini(self):
        self.TYPE = INFO.INI.findall("BALLSCREWPARAMS", "TYPE")[0]
        #print "*** self.TYPE = ", self.TYPE
        self.MODEL = INFO.INI.findall("BALLSCREWPARAMS", "MODEL")[0]
        self.DATE = INFO.INI.findall("BALLSCREWPARAMS", "DATE")[0]
        self.PART = INFO.INI.findall("BALLSCREWPARAMS", "PART")[0]
        self.LOGFILE = INFO.INI.findall("BALLSCREWPARAMS", "LOGFILE")[0]
        self.TRAVEL = INFO.INI.findall("BALLSCREWPARAMS", "TRAVEL")[0]
        #self.datalog.write("Номер изделия: " + self.PART + "\n")
        #self.datalog.write("Дата: " + self.DATE + "\n")
        #TODO обработка ошибок и исключений: 1) нет файла - сообщение и заполнение по умолчанию, создание конфига
        #TODO обработка ошибок и исключений: 2) нет ключей в конфиге - сообщение и заполнение по умолчанию

################################
# required handler boiler code #
################################

def get_handlers(halcomp, widgets, paths):
     return [HandlerClass(halcomp, widgets, paths)]
