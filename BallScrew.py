# This Python file uses the following encoding: utf-8
import sys
import os

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt5.QtCore import QFile


class BallScrew(QMainWindow):
    def __init__(self):
        super(BallScrew, self).__init__()
        uic.loadUi("BallScrew.ui", self)
        #self.load_ui()

    def onBtnFileSelect(self):
        fname = "123" #QFileDialog.getSaveFileName(self, 'Save LinuxCNC INI file',\
        #".","LinuxCNC INI (*.ini);;All Files (*.*)")
        edtFileSelect.setText(fname)

    def onBtnNext1(self):
        print "*** onBtnNext clicked"
        self.DRIVE = self.cmbDrive1.currentIndex()
        self.NAME = self.edtName1.text()
        self.DATE = self.edtDate1.text()
        self.PART = self.edtPart1.text()
        self.MODEL = self.cmbModel1.currentText()
        if(self.cmbType1.currentIndex()<4):
            self.load_ini(self.cmbType1.currentIndex())
            self.stackedWidget.setCurrentIndex(self.cmbType1.currentIndex()+1)
        else:
            self.load_ini(3)
            self.stackedWidget.setCurrentIndex(3)
        # self.close() только для случая многооконного интерфейса

    def onBtnNext2(self):
        #self.sender()
        if(self.sender() == self.btnNext21):
            pass
        elif(self.sender() == self.btnNext22):
            pass
        elif(self.sender() == self.btnNext23):
            pass
        elif(self.sender() == self.btnNext24):
            pass
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
