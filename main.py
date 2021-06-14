from pyqtgraph.functions import traceImage
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate
from PyQt5 import QtWidgets, QtCore, uic, QtGui, QtPrintSupport
from pyqtgraph import PlotWidget, plot
from PyQt5.uic import loadUiType
from PyQt5.QtWidgets import *   
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from scipy import signal
from os import path
import pyqtgraph as pg
import queue as Q
import pandas as pd
import numpy as np
import sys
import os
from fpdf import FPDF
import pyqtgraph.exporters
fileName = 'PDFReport.pdf'
pdf = SimpleDocTemplate(fileName, pagesize=letter)

#Connecting Between UI file and Py file
MAIN_WINDOW,_=loadUiType(path.join(path.dirname(__file__),"sigview.ui"))

# Class for plot widget that adds an id to each panel to control each panel
class myPlotWidget(PlotWidget):
    # Signal to send to other slots
    signal = pyqtSignal(int)

    def __init__(self, parent, id, background="default", **kwargs):
        super(myPlotWidget, self).__init__(parent=parent, background=background, **kwargs)
        self.id = id
        self.sceneObj.sigMouseClicked.connect(self.select_event) #Connecting the clicking event of the mouse to the select_event function

    def select_event(self):
        self.signal.emit(self.id)
        self.setStyleSheet("border: 2px solid rgb(0, 0, 255);") #Adds border to panel when selected by mouse

# MainClass of the application
class MainApp(QMainWindow,MAIN_WINDOW):
    # Number of Graphs, start from 0 at the start
    numOfGraphs = 0
    
    # Current selected widget by the user
    currentSelected = 0

    # The previous selected widget
    previousSelectedWidget = 0

    # List to add widgets with borders
    borderList = list()

    listX = [0] * 3
    y = [0] * 3
    i = [0] * 3
    listY = [0] * 3
    plottedSignal = [0] * 3 #Three signals
    timer = [0] * 3 #Three timers one for each signal

    def __init__(self,parent=None):
        super(MainApp,self).__init__(parent)
        QMainWindow.__init__(self)
        self.setupUi(self)
        self.Toolbar()
        self.Menubar()

        # Initialize graph widgets
        self.graphWidget1 = 0
        self.graphWidget2 = 0
        self.graphWidget3 = 0

        # Initialize spectogram widgets
        self.spectWidget1 = 0
        self.spectWidget2 = 0
        self.spectWidget3 = 0

        # list of graph widgets
        self.graphWidgets = [
            self.graphWidget1,
            self.graphWidget2,
            self.graphWidget3,
        ]

        # list of spectogram widgets
        self.spectWidgets = [
            self.spectWidget1,
            self.spectWidget2,
            self.spectWidget3,
        ]

    #connecting menubar buttons to their functions
    def Menubar(self):
        self.actionOpen_signal.triggered.connect(self.BrowseSignal)
        self.actionSave_signal_as.triggered.connect(self.printPDF)
        self.actionExit.triggered.connect(self.close)
        self.ClearSignal.triggered.connect(self.clearSignal)
        self.AddChannel.triggered.connect(self.addNewPanel)
        self.DeleteChannel.triggered.connect(self.deleteChannel)
        self.actionSignal1_2.triggered.connect(lambda checked: (self.receiveData(1)))
        self.actionSignal2_2.triggered.connect(lambda checked: (self.receiveData(2)))
        self.actionSignal3.triggered.connect(lambda checked: (self.receiveData(3)))
 
    #connecting toolbar buttons to their functions
    def Toolbar(self):
        self.OpenSignalBtn.triggered.connect(self.BrowseSignal)
        self.Beginning.triggered.connect(self.beginning)  
        self.LeftScroll.triggered.connect(self.ScrollLeft)  
        self.PlayBtn.triggered.connect(self.playSignal)    
        self.Pause.triggered.connect(self.pauseSignal)
        self.End.triggered.connect(self.end)
        self.RightScroll.triggered.connect(self.ScrollRight)
        self.ZoomIn.triggered.connect(self.zoomIn) 
        self.ZoomOut.triggered.connect(self.zoomOut) 
        self.AddPanel.triggered.connect(self.addNewPanel) 
        self.DeletePanel.triggered.connect(self.deleteChannel) 
        self.spectrogram.triggered.connect(self.spectro) 
        self.PDF.triggered.connect(self.printPDF)

    def receiveData(self, data):
        print("Data sent is", data) #for debugging
        MainApp.currentSelected = data
        self.graphWidgets[data - 1].setMinimumSize(QtCore.QSize(500, 200)) #Setting minimum size for graph widgets 

        MainApp.borderList.append(data)

        # Check if we clicked on another widget to remove border from the first widget
        if len(MainApp.borderList) == 2:
            if self.graphWidgets[MainApp.borderList[0] - 1] == None: #Pass if there is no previously selected widget
                pass
            else:
                self.graphWidgets[MainApp.borderList[0] - 1].setStyleSheet("border: 0px solid rgb(0, 0, 255);")

            # Remove the border from the first
            del MainApp.borderList[0]

    def addNewPanel(self):
        #Pop up warning if three pannels are full
        if MainApp.numOfGraphs == 3:
            # Popup warning
            self.show_popup("Maximum number of channels is 3", "You can't add more than 3 channels, you have to delete one first",)
        else:
            # Adjusting Queues (pop a channel from available panels group )
            MainApp.numOfGraphs += 1  # indexing
            # Setup Plot Configuration
            self.graphWidgets[MainApp.numOfGraphs -1] = myPlotWidget(self.centralwidget, id = MainApp.numOfGraphs )
            self.graphWidgets[MainApp.numOfGraphs -1].setEnabled(True)
            graphwideget = self.graphWidgets[MainApp.numOfGraphs -1]
            self.graphWidgetConfiguration(graphwideget)
            graphwideget.signal.connect(self.receiveData)

    def deleteChannel(self):
        num = MainApp.currentSelected  # ID of channel to be deleted
        # Check if no channel is selected
        if MainApp.currentSelected == 0:
            self.show_popup("No Channel Selected", "Choose an existing one")
        else:
            # add channel ID to available Panels group
            num -= 1  # indexing
            MainApp.numOfGraphs -= 1 # indexing
            # Close channel
            self.graphWidgets[num].close()
            self.spectWidgets[num].close()
            self.graphWidgets[num] = None
            self.spectWidgets[num] = None

            # Return currentSelected to normal state
            MainApp.currentSelected = 0

    #Browses for the signal to be plotted
    def BrowseSignal(self): 
        # Check if a channel is selected
        if MainApp.currentSelected == 0:
            self.show_popup("No Channel Selected", "Choose an existing Panel")
        else:
            fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self,"QFileDialog.getOpenFileName()", "","CSV Files (*.csv)")
            if fileName: 
                df=pd.read_csv(fileName,header=None)
                self.x=df[0]
                self.listX[MainApp.currentSelected - 1]=self.x.tolist() #list of numbers on x axis
                self.y[MainApp.currentSelected - 1]=df[1]
                self.listY[MainApp.currentSelected - 1]=[self.y[MainApp.currentSelected - 1][i] for i in range (len(self.y[MainApp.currentSelected - 1]))]
    
                self.i[MainApp.currentSelected - 1] = 0
                
                # Clear the plotting area and remove the previous signal
                self.clearSignal()

                #Plots the Browsed signal
                self.plottedSignal[MainApp.currentSelected - 1] =  self.graphWidgets[MainApp.currentSelected - 1].plotItem.plot(self.listX[MainApp.currentSelected - 1], self.listY[MainApp.currentSelected - 1], pen='b')
    
    #Function for playing the dynamic signal
    def playSignal(self):
        selectedWidget = MainApp.currentSelected

        # Check if No widget is selected
        if self.graphWidgets[MainApp.currentSelected - 1] == None:
            pass

        if MainApp.currentSelected == selectedWidget:
            self.timer[MainApp.currentSelected - 1] = QtCore.QTimer()
            self.timer[MainApp.currentSelected - 1].setInterval(25) #delay interval for dynamic signal
            self.timer[MainApp.currentSelected - 1].timeout.connect(self.playSignal) #connect timer to our dynamic signal
            self.timer[MainApp.currentSelected - 1].start() #Starting the timer

            self.listX[MainApp.currentSelected - 1] = self.listX[MainApp.currentSelected - 1][1:]  # Remove the first x element.

            
            self.listX[MainApp.currentSelected - 1].append(self.listX[MainApp.currentSelected - 1][self.i[MainApp.currentSelected - 1]]) #Add a new value

            self.listY[MainApp.currentSelected - 1] = self.listY[MainApp.currentSelected - 1][1:]  # Remove the first y element

            self.listY[MainApp.currentSelected - 1].append(self.y[MainApp.currentSelected - 1][self.i[MainApp.currentSelected - 1]]) 
            self.i[MainApp.currentSelected - 1] = self.i[MainApp.currentSelected - 1] + 1 

            self.plottedSignal[MainApp.currentSelected - 1].setData(self.listX[MainApp.currentSelected - 1][:self.i[MainApp.currentSelected - 1]], self.listY[MainApp.currentSelected - 1][:self.i[MainApp.currentSelected - 1]])

            self.graphWidgets[MainApp.currentSelected - 1].setXRange(self.listX[MainApp.currentSelected - 1][0] , self.listX[MainApp.currentSelected - 1][-1])
    
    def pauseSignal(self):
        self.timer[MainApp.currentSelected - 1].stop() #Stopping the timer in case of pausing signal

    def beginning(self):
        self.graphWidgets[MainApp.currentSelected - 1].setXRange(self.listX[MainApp.currentSelected - 1][0], self.listX[MainApp.currentSelected - 1][0] + 1) #Resets graph to the beggining of plotted point

    def end(self):
        self.graphWidgets[MainApp.currentSelected - 1].setXRange(self.listX[MainApp.currentSelected - 1][-1] - 1 , self.listX[MainApp.currentSelected - 1][-1]) #Sets graph to the end plotted point

    def zoomIn(self):
        self.graphWidgets[MainApp.currentSelected - 1].plotItem.getViewBox().scaleBy(x=0.5, y=1) #Increases the scale of X axis and Y axis

    def zoomOut(self):
        self.graphWidgets[MainApp.currentSelected - 1].plotItem.getViewBox().scaleBy(x=2, y=1) #Decreases scale of X axis and Y axis 

    def ScrollLeft(self):
        self.graphWidgets[MainApp.currentSelected - 1].plotItem.getViewBox().translateBy(x=-0.1, y=0)

    def ScrollRight(self):
        self.graphWidgets[MainApp.currentSelected - 1].plotItem.getViewBox().translateBy(x=0.1, y=0)
        
    def clearSignal(self):
        # clear the previous data line
        self.graphWidgets[MainApp.currentSelected - 1].plotItem.clear()

    def close(self):
        QCoreApplication.instance().quit()

    def spectro(self):
        
        self.spectWidgets[MainApp.currentSelected -1] = myPlotWidget(self.centralwidget, id = ((MainApp.currentSelected)+ 3 ))
        
        self.verticalLayout_2.addWidget(self.spectWidgets[MainApp.currentSelected -1])

        # self.spectWidgets[MainApp.numOfGraphs -1].setEnabled(True)
        win = self.spectWidgets[MainApp.currentSelected -1 ]
        self.spectWidgetConfiguration(win)
        sampling_freq = 1000    #10e3
        listY = self.y[MainApp.currentSelected - 1]   
        frequency, time, spectrogram = signal.spectrogram(listY, sampling_freq) # spectrogram ( time series of measurement values , sampling freq ) = frequency : ndarray Array of sample frequencies.  
                                            # time : ndarray Array of segment times.  
                                            # spectrogram : ndarray Spectrogram of x. By default, the last axis of spectrogram corresponds to the segment times.  

        # Interpret image data as row-major instead of col-major
        pg.setConfigOptions(imageAxisOrder='row-major')

        # Item for displaying image datas
        self.img = pg.ImageItem()
        win.addItem(self.img)
        # Add a histogram with which to control the gradient of the image
        self.hist = pg.HistogramLUTItem()
        # Link the histogram to the image
        self.hist.setImageItem(self.img)
        # Fit the min and max levels of the histogram to the data available
        self.hist.setLevels(np.min(spectrogram), np.max(spectrogram))
        # This gradient is roughly comparable to the gradient used by Matplotlib
        # You can adjust it and then save it using hist.gradient.saveState()
        self.hist.gradient.restoreState(
                {'mode': 'rgb',
                'ticks': [(0.5, (0, 182, 188, 255)),
                        (1.0, (246, 111, 0, 255)),
                        (0.0, (75, 0, 113, 255))]})
        # spectrogram contains the amplitude for each pixel
        self.img.setImage(spectrogram)
        # Scale the X and Y Axis to time and frequency (standard is pixels)
        self.img.scale(time[-1]/np.size(spectrogram, axis=1),
                frequency[-1]/np.size(spectrogram, axis=0))   
        # Limit panning/zooming to the spectrogram
        win.setLimits(xMin=0, xMax=time[-1], yMin=0, yMax=frequency[-1])

        # Add labels to the axis
        win.setLabel('bottom', "Time", units='s')
        # If you include the units, Pyqtgraph automatically scales the axis and adjusts the SI prefix (in this case kHz)
        win.setLabel('left', "Frequency", units='Hz')

    def graphWidgetConfiguration(self, graphWidget):
        """
        Sets the plotting configurations
        :return:
        """
        graphWidget.setMinimumSize(QtCore.QSize(500, 200))
        graphWidget.plotItem.setTitle("Channel " + str(MainApp.numOfGraphs ) )
        graphWidget.plotItem.showGrid(True, True, alpha=0.8)
        graphWidget.setBackground('w')
        graphWidget.plotItem.setLabel("bottom", text="Time (s)")
        graphWidget.plotItem.setLabel("left", text="Amplitude (mV)")
        self.verticalLayout.addWidget(graphWidget)

    def spectWidgetConfiguration(self , spectWidget):
        """
        Sets the plotting configurations
        :return:
        """
        spectWidget.setMinimumSize(QtCore.QSize(500, 200))
        spectWidget.plotItem.setTitle("Spectogram" + str(MainApp.currentSelected))
        spectWidget.setBackground('w')
        spectWidget.plotItem.setLabel("bottom", text="segment times")
        spectWidget.plotItem.setLabel("left", text="sample frequencies")
        self.verticalLayout_2.addWidget(spectWidget)

    def show_popup(self, message, info):
        msg = QMessageBox()
        msg.setWindowTitle("Popup Message")
        msg.setText(message)
        msg.setIcon(QMessageBox.Warning)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setDefaultButton(QMessageBox.Ok)
        msg.setInformativeText(info)
        x = msg.exec_()

    def printPDF(self):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 15)
        pdf.set_xy(0,0)
        
        for i in range (self.numOfGraphs):

            pdf.cell(0, 10,ln=1,align='C')
            exporter = pg.exporters.ImageExporter(self.graphWidgets[i].plotItem)               
            exporter.parameters()['width'] = 250  
            exporter.parameters()['height'] = 250         
            exporter.export('fileName'+ str(i) +'.png')
            pdf.image('fileName'+ str(i) +'.png',x=None,y=None, w=180,h=70)

            if self.spectWidgets[i] == None:
                pass
            else:
                pdf.cell(0, 10,ln=1,align='C')
                exporter = pg.exporters.ImageExporter(self.spectWidgets[i].plotItem)               
                exporter.parameters()['width'] = 250  
                exporter.parameters()['height'] = 250         
                exporter.export('fileName'+ str(i+3) +'.png')
                pdf.image('fileName'+ str(i+3) +'.png',x=None,y=None, w=180,h=70)
            
        pdf.output('Report.pdf')

def main():
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec_())


if __name__=='__main__':
    main()