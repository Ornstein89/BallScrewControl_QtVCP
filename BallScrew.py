# This Python file uses the following encoding: utf-8
import sys, os, configparser

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QPushButton
from PyQt5.QtWidgets import QLayout, QSizePolicy
from PyQt5.QtCore import QFile

# пакет для xlsx
import openpyxl

class BallScrew(QMainWindow):
    def __init__(self):
        super(BallScrew, self).__init__()
        uic.loadUi("BallScrew.ui", self)
        self.initGUI()
        self.initParamsGUIMatch()
        #self.load_ui()

    def onBtnFileSelect(self):
        fname = QFileDialog.getSaveFileName(self, 'Save log file',
        ".","LOG (*.log);;Text (*.txt);;All Files (*.*)")
        #TODO не выбран
        self.LOGFILE = fname[0]
        self.edtFileSelect.setText(self.LOGFILE)

    def onBtnNext1(self):
        print "*** onBtnNext clicked"
        self.wgtNext2.show()
        self.DRIVE = self.cmbDrive.currentIndex()
        self.NAME = self.edtName.text()
        self.DATE = self.edtDate.text()
        self.PART = self.edtPart.text()
        self.MODEL = self.cmbModel.currentText()
        if (self.cmbType.currentIndex()<0):
            pass
        elif(self.cmbType.currentIndex()<4):
            self.TYPE_N = self.cmbType.currentIndex()+1
            print "*** currentIndex() = ", self.cmbType.currentIndex()
            print "*** self.TYPE_N = ", self.TYPE_N
        else:
            self.TYPE_N = 4
        self.loadIni(self.TYPE_N)
        self.stackedWidget.setCurrentIndex(self.TYPE_N)
        self.checkGUI2()
        self.onEdtFileChanged()

    def onBtnNext2(self):
        #запись ini-файла
        self.save_ini(self.stackedWidget.currentIndex())
        #запуск linuxcnc с ini-файлом
        #os.system(u"linuxcnc ./"+self.NAME.decode('utf-8'))
        #os.system(u"linuxcnc ./"+self.NAME.encode('utf-8')) # вариант опробовать
        os.system(("linuxcnc ./" + self.edtName.text()).encode('utf-8')) # вариант опробовать
        # вариант опробовать os.system(u"linuxcnc ./"+unicode(self.NAME))
        return

    def onBtnBack(self):
        self.wgtNext2.hide()
        self.stackedWidget.setCurrentIndex(0)
        self.checkGUI1()

    def onForm1DataChanged(self):
        self.MODEL = self.cmbModel.currentText()
        self.PART = self.edtPart.text()
        self.TYPE = self.cmbType.currentText().replace(' ', '_')
        self.DATE = self.edtDate.text()

        self.edtName.setText(self.MODEL + '__' + self.PART + '__'
                        + self.TYPE + '__' + self.DATE + '__.ini')
        self.checkGUI1()

    def onEdtFileChanged(self):
        self.LOGFILE = self.edtFileSelect.text()
        self.checkGUI2()

    def initGUI(self):
        #видимость/невидимость, активность/неактивность
        self.stackedWidget.setCurrentIndex(0)
        self.btnNext1.setEnabled(False)
        self.btnNext2.setEnabled(False)
        self.wgtNext2.setVisible(False)

        self.loadExcelFile()
        self.checkGUI1()

    def checkGUI1(self):  # проверка состояния формы 1 и разрешение перехода на форму 2
        canNext = ( (self.MODEL != "")
            and (self.cmbDrive.currentIndex >= 0)
            and (self.TYPE != "")
            and (self.PART != ""))
        #TODO перенастроить на переменные self.TYPE и др.
        if canNext:
            self.btnNext1.setEnabled(True)
        else:
            self.btnNext1.setEnabled(False)
            #TODO уведомление "Заполните поля корректными значениями"

    def checkGUI2(self):  # проверка состояния формы 2 и разрешение запуска linuxcnc (форма 3)
        canNext2 = self.edtFileSelect.text().endswith(".log")
        if canNext2:
            self.btnNext2.setEnabled(True)
        else:
            self.btnNext2.setEnabled(False)

    def loadExcelFile(self):
        database_file = 'База данных испытаний.xlsx'
        try:
            wb = openpyxl.load_workbook(filename = database_file, read_only = True)
            print("*** OK load_workbook")
            #for sheet in wb:
            #    print(sheet.title)
            ws = wb[wb.sheetnames[1]]
            print("*** OK wb[\"Modeli\"]")
            list_test_types = []
            row = 1
            print("*** OK value 1", ws.cell(row = 1, column = 1).value)
            print("*** OK value 2", ws.cell(row = 2, column = 1).value)
            print("*** OK value 3", ws.cell(row = 3, column = 1).value)

            while(ws.cell(row = row, column = 1).value is not None):
                list_test_types.append(ws.cell(row = row, column = 1).value)
                print("*** OK row=", row, " appended, value = ",
                      ws.cell(row = row, column = 1).value)
                row = row + 1
            print("*** list_test_types = ", list_test_types)
            self.cmbModel.addItems(list_test_types)
            print("*** OK ", addItems)
        except:
            print("*** Не удалось открыть файл базы данных \"", database_file, "\"")

    def loadIni(self, n_form):
        config = configparser.ConfigParser(strict=False) # strict=False - разрешение повторов имени ключа
        config.optionxform = str # имена ключей не будут приведены к нижнему регистру
        config.read('BallScrew.ini')
        for key, control in self.params_and_controls_dict[n_form-1].items():
            val_string = config['TYPE_'+str(n_form)][key]
            control.setMinimum(float(config['TYPE_'+str(n_form)][key+'_MIN']))
            control.setMaximum(float(config['TYPE_'+str(n_form)][key+'_MAX']))
            control.setValue(float(val_string))
            #создать рядом с элементом управления кнопку сброса
            parent = control.parentWidget()
            layout = control.parentWidget().layout()
            index = layout.indexOf(control);
            button = QPushButton(val_string, parent)
            #button.setMaximumSize(control.size())
            button.setMaximumHeight(control.height())
            button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            location = layout.getItemPosition(index)
            control.parentWidget().layout().addWidget(button,location[0],location[1]+1)
            button.clicked.connect(lambda state, p_control=control, v=float(val_string): p_control.setValue(v))

    def initParamsGUIMatch(self):
        self.params_and_controls_dict = (
            {'GEAR': self.spnGear21,
            'PITCH' : self.spnPitch21,
            'TRAVEL' : self.spnTravel21,
            'NOM_VEL' : self.spnNom_Vel21,
            'NOM_ACCEL' : self.spnNom_Accel21},
            {'GEAR' : self.spnGear22,
            'NOM_VEL' : self.spnNom_Vel22,
            'BRAKE_TORQUE' : self.spnBrake_Torque22,
            'DURATION' : self.spnDuration22},
            {'GEAR' : self.spnGear23,
            'PITCH' : self.spnPitch23,
            'NOM_DSP_IDLE' : self.spnNom_Dsp_Idle23,
            'NOM_VEL_IDLE' : self.spnNom_Vel_Idle23,
            'NOM_ACCEL_IDLE' : self.spnNom_Accel_Idle23,
            'NOM_DSP_MEASURE' : self.spnNom_Dsp_Measure23,
            'NOM_VEL_MEASURE' : self.spnNom_Vel_Measure23,
            'NOM_ACCEL_MEASURE' : self.spnNom_Accel_Measure23,
            'NOM_LOAD' : self.spnNom_Load23,
            'NOM_POS_MEASURE' : self.spnNom_Pos_Measure23},
            {'GEAR' : self.spnGear24,
            'PITCH' : self.spnPitch24,
            'NOM_TRAVEL' : self.spnNom_Travel24,
            'NOM_OMEGA' : self.spnNom_Omega24,
            'NOM_ACCEL_COEFF' : self.spnNom_Accel_Coeff24,
            'NOM_F1' : self.spnNom_F1_24,
            'NOM_F2' : self.spnNom_F2_24,
            'OVERLOAD_COEFF' : self.spnOverload_Coeff24,
            'DWELL' : self.spnDwell24,
            'N' : self.spnN24,
            'LOG_FREQ' : self.spnLog_Freq24} )

    def save_ini(self, n_form):
        # создать config из шаблона
        config = configparser.ConfigParser(strict=False) # strict=False - разрешение повторов имени ключа
        config.optionxform = str # имена ключей не будут приведены к нижнему регистру
        config.read('BallScrewVCP_template.ini')
        # добавить значения из интерфейса в объект config
        config['BALLSCREWPARAMS'] = {}
        for key, control in self.params_and_controls_dict[n_form-1].items():
            config['BALLSCREWPARAMS'][key] = str(control.value())
            config['BALLSCREWPARAMS'][key+'_MIN'] = str(control.minimum())
            config['BALLSCREWPARAMS'][key+'_MAX'] = str(control.maximum())
        config['BALLSCREWPARAMS']['TYPE']=str(n_form) #TODO
        config['BALLSCREWPARAMS']['DATE']=self.DATE
        config['BALLSCREWPARAMS']['MODEL']="TODO change on release" #self.MODEL
        config['BALLSCREWPARAMS']['PART']=self.PART
        config['BALLSCREWPARAMS']['LOGFILE']=self.LOGFILE
        #TODO config['BALLASREWPARAMS']['HAL']=
        # запись заполненного config в ini-файл
        configfile = open(self.NAME, 'w')
        config.write(configfile)
        configfile.close()

        #TODO обработка ошибок и исключений: нельзя открыть шаблон, нельзя открыть новый ini и пр.
        #TODO предупреждение о перезаписи
        return

    def onBtnTempShow1(self):
        self.stackedWidget.setCurrentIndex(0)
        pass

    def onBtnTempShow21(self):
        self.stackedWidget.setCurrentIndex(1)
        pass

    def onBtnTempShow22(self):
        self.stackedWidget.setCurrentIndex(2)
        pass

    def onBtnTempShow23(self):
        self.stackedWidget.setCurrentIndex(3)
        pass

    def onBtnTempShow24(self):
        self.stackedWidget.setCurrentIndex(4)
        pass

    # для PySide
    # def load_ui(self):
    #     loader = QUiLoader()
    #     path = os.path.join(os.path.dirname(__file__), "BallScrew.ui")
    #     ui_file = QFile(path)
    #     ui_file.open(QFile.ReadOnly)
    #     loader.load(ui_file, self)
    #     ui_file.close()

if __name__ == "__main__":
    app = QApplication([])
    widget = BallScrew()
    widget.show()
    sys.exit(app.exec_())
