# This Python file uses the following encoding: utf-8
import sys, os, configparser

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog
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
        fname = QFileDialog.getSaveFileName(self, 'Save LinuxCNC INI file',
        ".","LinuxCNC INI (*.ini);;All Files (*.*)")
        #TODO не выбран
        self.edtFileSelect.setText(fname[0])

    def onBtnNext1(self):
        print "*** onBtnNext clicked"
        self.wgtNext2.show()
        self.DRIVE = self.cmbDrive.currentIndex()
        self.NAME = self.edtName.text()
        self.DATE = self.edtDate.text()
        self.PART = self.edtPart.text()
        self.MODEL = self.cmbModel.currentText()
        if(self.cmbType.currentIndex()<4):
            #self.load_ini(self.cmbType.currentIndex())
            #TODO загрузить файл с min/max-значениями и применить из к spinEdit
            self.stackedWidget.setCurrentIndex(self.cmbType.currentIndex()+1)
        else:
            #self.load_ini(3)
            #TODO загрузить файл с min/max-значениями и применить из к spinEdit
            self.stackedWidget.setCurrentIndex(3)
        # self.close() только для случая многооконного интерфейса

    def onBtnNext2(self):
        #запись ini-файла
        self.save_ini(self.stackedWidget.currentIndex())
        #TODO запуск linuxcnc с ini-файлом
        return

    def onForm1DataChanged(self):
        self.checkGUI1()

    def onEdtFileChanged(self):
        self.checkGUI2()

    def initGUI(self):
        self.btnNext1.setEnabled(False)
        self.btnNext2.setEnabled(False)
        self.wgtNext2.setVisible(False)
        self.loadExcelFile()

    def checkGUI1(self):  # проверка состояния формы 1 и разрешение перехода на форму 2
        canNext = ( (self.cmbModel.currentIndex >= 0)
            and (self.cmbDrive.currentIndex >= 0)
            and (self.cmbType.currentIndex >= 0)
            and (not self.edtPart.text()=="")
            and (not self.edtDate.text()=="")
            and (not self.edtName.text()=="") )
        #TODO перенастроить на переменные self.TYPE и др.
        if canNext:
            self.btnNext1.setEnabled(True)
        else:
            self.btnNext1.setEnabled(False)
            #TODO уведомление "Заполните поля корректными значениями"

    def checkGUI2(self):  # проверка состояния формы 2 и разрешение запуска linuxcnc (форма 3)
        canNext2 = len(self.edtFileSelect.text()) > 0
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
        config = configparser.ConfigParser(strict=False)
        config.read('BallScrewVCP_template.ini')
        # добавить значения из интерфейса в объект config
        config['BALLASCREWPARAMS'] = {}
        for key in self.params_and_controls_dict[n_form]:
            config['BALLASCREWPARAMS'][key] = str(self.params_and_controls_dict[n_form][key].value())
        config['BALLASCREWPARAMS']['TYPE']=str(n_form)
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
