'''
    NRGsuite: PyMOL molecular tools interface
    Copyright (C) 2011 Gaudreault, F., Morency, LP. & Najmanovich, R.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''

from __future__ import print_function

'''
@title: GetCleft - Interface - Default tab

@summary: This is the interface of GetCleft application accessible via the
          PyMOL menu (NRGsuite).

@organization: Najmanovich Research Group
@creation date:  Oct. 19, 2010
'''

import sys
if sys.version_info[0] < 3:
    from Tkinter import *
    import tkFileDialog
    import tkMessageBox
else:
    from tkinter import *
    import tkinter.filedialog as tkFileDialog
    import tkinter.messagebox as tkMessageBox

from subprocess import Popen, PIPE
from time import time
from glob import glob

import os
import re
import Tabs
import General
import CleftObj
import BindingSite

import threading
import Color
import pickle

if __debug__:
    from pymol import cmd
    import General_cmd

#=========================================================================================
'''                        ---   STARTING GETCLEFT  ---                                '''
#=========================================================================================
class Start(threading.Thread):

    # in milliseconds
    TKINTER_UPDATE_INTERVAL = 100
    
    def __init__(self, top, queue, cmdline):
                 
        threading.Thread.__init__(self)

        self.top = top
        self.queue = queue
        
        self.GetCleft = self.top.top

        self.cmdline = cmdline
        print(self.cmdline)
        
        # Start the thread
        self.start()

    def run(self):
       
        print("GetCleft starting thread has begun.")
        
        try:
            if self.GetCleft.OSid == 'WIN':
                self.GetCleft.Run = Popen(self.cmdline, shell=False, stderr=PIPE)
            else:
                self.GetCleft.Run = Popen(self.cmdline, shell=True, stderr=PIPE)
                
            self.GetCleft.Run.wait()

            if self.GetCleft.Run.returncode != 0:
                self.GetCleft.ProcessError = True
                
        except OSError:
            print('  FATAL ERROR (OSError exception raised): Could not run the executable GetCleft.')
            print('  Make sure you downloaded NRGsuite for the right platform.')
            self.GetCleft.ProcessError = True

        except ValueError:
        	print('  FATAL ERROR (ValueError exception raised): Pipe opened with invalid arguments.')
        	self.GetCleft.ProcessError = True

        self.GetCleft.Run = None
        self.GetCleft.ProcessRunning = False
        
        self.queue.put(lambda: self.top.GetCleftRunning(False))

        print("GetCleft starting thread has ended.")
        
#=========================================================================================
'''                        ---  GETCLEFT's DEFAULT FRAME  ---                          '''
#=========================================================================================     
class Default(Tabs.Tab):

    def Def_Vars(self):

        self.TempBindingSite = BindingSite.BindingSite()

        self.NbCleft = StringVar()
        self.MinRadius = StringVar()
        self.MaxRadius = StringVar()
        self.MessageValue = StringVar()

        self.FetchPDB = StringVar()
        self.ResiduValue = StringVar()
        self.OutputFileValue = StringVar()
                        
        self.defaultOption = StringVar()
        self.listResidues = list()

        self.ColorList = list()
        self.ColorHex = list()

    def Init_Vars(self):

        self.FetchPDB.set('')
        self.NbCleft.set('5')
        self.MinRadius.set('1.50')
        self.MaxRadius.set('4.00')
        self.OutputFileValue.set('')
        self.ResiduValue.set('')
        self.MessageValue.set('')
        self.defaultOption.set('')

        self.listResidues = []
        self.PartitionColor = 'partition'
        self.LastdefaultOption = ''
        
    ''' ==================================================================================
    FUNCTION Trace: Adds a callback function to StringVars
    ==================================================================================  '''  
    def Trace(self):

        try:
            self.defaultOptionTrace = self.defaultOption.trace('w',self.Toggle_defaultOption)

            self.MaxRadiusTrace = self.MaxRadius.trace('w', lambda *args, **kwargs:
                                                            self.Validate_Field(input=self.EntryMaxRadius, var=self.MaxRadius, min=self.MinRadius,
                                                            max=5.00, ndec=2, tag='Maximum radius', _type=float))

            self.MinRadiusTrace = self.MinRadius.trace('w', lambda *args, **kwargs:
                                                            self.Validate_Field(input=self.EntryMinRadius, var=self.MinRadius, min=0.50,
                                                            max=self.MaxRadius, ndec=2, tag='Minimum radius', _type=float))
                     
            self.NbCleftTrace = self.NbCleft.trace('w', lambda *args, **kwargs:
                                                        self.Validate_Field(input=self.EntryNbCleft, var=self.NbCleft, min=1,
                                                        max=20, ndec=-1, tag='Number of clefts', _type=int))
            
        except:
            pass

    ''' ==================================================================================
    FUNCTION Del_Trace: Deletes observer callbacks
    ==================================================================================  '''  
    def Del_Trace(self):

        try:
            self.defaultOption.trace_vdelete('w',self.defaultOptionTrace)
            self.MaxRadius.trace_vdelete('w',self.MaxRadiusTrace)
            self.MinRadius.trace_vdelete('w',self.MinRadiusTrace)
            self.NbCleft.trace_vdelete('w',self.NbCleftTrace)
        except:
            pass

    ''' ==================================================================================
    FUNCTION After_Show: Actions related after showing the frame
    ==================================================================================  '''  
    def After_Show(self):
                        
        self.Btn_RefreshOptMenu_Clicked()
        
        if self.LastdefaultOption != '' and General_cmd.object_Exists(self.LastdefaultOption):
            self.defaultOption.set(self.LastdefaultOption)
    
    ''' ==================================================================================
    FUNCTION Frame: Displays the Default Frame
    ==================================================================================  '''          
    def Frame(self):
                
        self.fDefault = Frame(self.top.fMiddle, relief=RIDGE)

        #==================================================================================
        #                           SELECTION OF STRUCTURE
        #==================================================================================                
        fStructure = Frame(self.fDefault)
        #fStructure.pack(side=TOP, padx=5, pady=5, fill=X, expand=True)

        fStructureLine1 = Frame(fStructure)
        fStructureLine1.pack(side=TOP, fill=X, expand=True)
        fStructureLine2 = Frame(fStructure)
        fStructureLine2.pack(side=TOP, fill=X, expand=True)

        Label(fStructureLine1, text='Retrieve a structure', font=self.top.font_Title).pack(side=LEFT)

        # Get a PDB File from a file on your harddrive
        #Button(fStructureLine2, text='Open target', command=self.Btn_OpenPDB_Clicked, font=self.font_Text).pack(side=LEFT, padx=5)
        
        # Download a PDB File from the internet
        Button(fStructureLine2, text='Download', command=self.Btn_DownloadPDB_Clicked, font=self.font_Text, width=10).pack(side=RIGHT, padx=5)
        Entry(fStructureLine2, textvariable=self.FetchPDB, width=10, background='white', font=self.font_Text, justify=CENTER).pack(side=RIGHT)
        Label(fStructureLine2, text='Enter the PDB code:', font=self.font_Text, justify=CENTER).pack(side=RIGHT, padx=5)

        fSelection = Frame(self.fDefault)
        fSelection.pack(side=TOP, padx=5, pady=5, fill=X, expand=True)
        fSelectionLine1 = Frame(fSelection)
        fSelectionLine1.pack(side=TOP, fill=X, expand=True)
        fSelectionLine2 = Frame(fSelection)
        fSelectionLine2.pack(side=TOP, fill=X, expand=True)

        Label(fSelectionLine1, text='Select a structure', font=self.top.font_Title).pack(side=LEFT)

        # List of selections
        Label(fSelectionLine2, text='PyMOL objects/selections:', font=self.font_Text, justify=LEFT).pack(side=LEFT, padx=5)
        
        # Refresh the list with the selections in Pymol
        Button(fSelectionLine2, text='Refresh', command=self.Btn_RefreshOptMenu_Clicked, font=self.font_Text, width=10).pack(side=RIGHT, padx=5)

        optionTuple = ('',)
        self.optionMenuWidget = OptionMenu(*(fSelectionLine2, self.defaultOption) + optionTuple)
        self.optionMenuWidget.config(bg=self.Color_White, font=self.font_Text, width=15)
        self.optionMenuWidget.pack(side=RIGHT)
                
        #==================================================================================
        '''                     --- Basic GetCleft Options ---                          '''
        #==================================================================================
        #-----------------------------------------------------------------------------------------        
        fBasic = Frame(self.fDefault, border=0, relief=RAISED)
        fBasic.pack(fill=X, expand=True, padx=5, pady=5, ipady=3)
        fBasicLine1 = Frame(fBasic)
        fBasicLine1.pack(fill=X, side=TOP)
        fBasicLine2 = Frame(fBasic)
        fBasicLine2.pack(fill=X, side=TOP)
        fBasicLine3 = Frame(fBasic)
        fBasicLine3.pack(fill=X, side=TOP)
        fBasicLine4 = Frame(fBasic)
        fBasicLine4.pack(fill=X, side=TOP)
        fBasicLine5 = Frame(fBasic)
        fBasicLine5.pack(fill=X, side=TOP)

        Label(fBasicLine1, text='Parametrization', font=self.top.font_Title).pack(side=LEFT)

        Label(fBasicLine2, text='Insert spheres radii:', font=self.top.font_Text).pack(side=LEFT)

        self.EntryMaxRadius = Entry(fBasicLine2, width=5, textvariable=self.MaxRadius, background='white', justify=CENTER, font=self.top.font_Text)
        self.EntryMaxRadius.pack(side=RIGHT)
        Label(fBasicLine2, text='Max:', font=self.top.font_Text).pack(side=RIGHT, padx=2)

        self.EntryMinRadius = Entry(fBasicLine2, width=5, textvariable=self.MinRadius, background='white', justify=CENTER, font=self.top.font_Text)
        self.EntryMinRadius.pack(side=RIGHT)
        Label(fBasicLine2, text='Min:', font=self.top.font_Text).pack(side=RIGHT, padx=2)
        
        self.ValidMaxRadius = [ 1, False, self.EntryMaxRadius ]
        self.ValidMinRadius = [ 1, False, self.EntryMinRadius ]
        
        Label(fBasicLine3, text='Residue in contact (e.g. ALA13A):', font=self.top.font_Text).pack(side=LEFT)
        self.EntryResidu = Entry(fBasicLine3,textvariable=self.ResiduValue, background='white', justify=CENTER, font=self.top.font_Text)
        self.EntryResidu.pack(side=RIGHT)

        Label(fBasicLine4, text='Number of clefts to show:', font=self.top.font_Text).pack(side=LEFT)
        self.EntryNbCleft = Entry(fBasicLine4, width=8, textvariable=self.NbCleft, background='white', justify=CENTER, font=self.top.font_Text)
        self.EntryNbCleft.pack(side=RIGHT)
        self.ValidNbCleft = [ 1, False, self.EntryNbCleft ]

        #Label(fBasicLine5, text='Output cleft basename:', font=self.top.font_Text).pack(side=LEFT)
        self.EntryOutput = Entry(fBasicLine5, textvariable=self.OutputFileValue, background='white', font=self.top.font_Text, justify=CENTER)
        #self.EntryOutput.pack(side=RIGHT)
        self.ValidOutput = [ 1, False, self.EntryOutput ]

        #Button(fBasicLine5, text='Advanced parameters', font=self.top.font_Text, width=20, relief=RIDGE, command=self.Btn_AdvancedOptions).pack(side=RIGHT)

        #==================================================================================
        '''                           --- BUTTONS AREA ---                              '''
        #==================================================================================
        fButtons = Frame(self.fDefault)
        fButtons.pack(fill=X, expand=True, padx=5, pady=5)
                                                  
        # Starts the GetCleft application
        self.Btn_StartGetCleft = Button(fButtons, text='Start', command=self.Btn_StartGetCleft_Clicked, font=self.top.font_Text)
        self.Btn_StartGetCleft.pack(side=LEFT)
        self.Btn_StartGetCleft.config(state='disabled')

        # Clear PyMOL elements
        Btn_Clear = Button(fButtons, text='Clear', command=self.Btn_Clear_Clicked, font=self.top.font_Text)
        Btn_Clear.pack(side=LEFT)

        #==================================================================================
        '''                         --- COLOR CHART AREA ---                            '''
        #==================================================================================
        #-----------------------------------------------------------------------------------------        
        fChart = Frame(self.fDefault)
        fChart.pack(fill=X, expand=True, padx=5, side=BOTTOM)
        fChartLine1 = Frame(fChart)
        fChartLine1.pack(fill=X, expand=True)
        fChartLine2 = Frame(fChart)
        fChartLine2.pack(fill=X, expand=True)
        fChartLine3 = Frame(fChart)
        fChartLine3.pack(fill=X, expand=True)

        #Label(fChartLine1, text='Clefts color chart', font=self.top.font_Title).pack(side=TOP)
        #Label(fChartLine2, text='Index', width=10, font=self.top.font_Text).pack(side=LEFT)        

        fSim_Prog = Frame(fChartLine2, border=1, relief=SUNKEN, width=400, height=25)
        fSim_Prog.pack(side=TOP)#, anchor=W) 
        self.ChartBar = Canvas(fSim_Prog, bg=self.top.Color_Grey, width=400, height=25, highlightthickness=0, relief='flat', bd=0)
        self.ChartBar.pack(fill=BOTH, anchor=W)

        #==================================================================================
        '''        --- The DISPLAY options for the CLEFT and SPHERES ---                '''
        #==================================================================================
        fDisplay = Frame(self.fDefault)
        fDisplay.pack(side=TOP, fill=X, padx=5, pady=5)
        fDisplayLine1 = Frame(fDisplay)
        fDisplayLine1.pack(side=TOP, fill=X)
        fDisplayLine2 = Frame(fDisplay)
        fDisplayLine2.pack(side=TOP, fill=X)
        fDisplayLine3 = Frame(fDisplay)
        fDisplayLine3.pack(side=TOP, fill=X)
        
        #Label(fDisplayLine1, text='Display options', font=self.top.font_Title).pack(side=LEFT)
        #Checkbutton(fDisplayLine2, text='Atoms', width=20, variable=self.intChkAtoms, font=self.top.font_Text, justify=LEFT).pack(side=LEFT) 
        #Radiobutton(fDisplayLine2, text='Spheres', variable=self.RadioCLF, value='sphere', font=self.top.font_Text).pack(side=LEFT)
        #Radiobutton(fDisplayLine2, text='Surface', variable=self.RadioCLF, value='surface', font=self.top.font_Text).pack(side=LEFT)
        #Checkbutton(fDisplayLine3, text='Clefts', width=20, variable=self.intChkClefts, font=self.top.font_Text, justify=LEFT).pack(side=LEFT)

        self.Validator = [ self.ValidNbCleft, self.ValidMinRadius, self.ValidMaxRadius, self.ValidOutput ]
       
        return self.fDefault
        
    ''' ==================================================================================
    FUNCTION Btn_Clear_Clicked: Clear the temp dir of clefts and delete associated clefts 
    ==================================================================================  '''
    def Btn_Clear_Clicked(self):
        
        # Delete Cleft/Sphere objects in PyMOL
        for Cleft in self.TempBindingSite.listClefts:
            if self.PyMOL:
                try:
                    cmd.delete(Cleft.CleftName)
                    cmd.refresh()
                except:
                    pass
        
        self.TempBindingSite.Clear_Cleft()

        # Clean temporary files
        self.top.Manage.Clean()
        
        self.top.Go_Step1()
        self.ChartBar.delete('all')
        
    ''' ==================================================================================
    FUNCTION Btn_StartGetCleft_Clicked: Run GetCleft and display the result in Pymol 
    ==================================================================================  '''
    def Btn_StartGetCleft_Clicked(self):

        if self.top.ValidateProcessRunning():
            return
            
        if self.Validate_Fields():
            self.DisplayMessage("  ERROR: Not all fields are validated.", 2)
            return
        
        try:
            TmpFile = os.path.join(self.top.GetCleftProject_Dir,'tmp.pdb')

            if self.PyMOL:
                if cmd.count_atoms(self.defaultOption.get()) == 0:
                    self.DisplayMessage("  ERROR: No atoms found for object/selection '" + self.defaultOption.get() + "'", 2)
                    return
                
                cmd.save(TmpFile, self.defaultOption.get(), 1)

        except:
            self.DisplayMessage("  ERROR: Could not save the object/selection '" + self.defaultOption.get() + "'", 2)
            return


        if self.ResiduValue.get() != '':
            
            # with HETATM groups
            if General.store_Residues(self.listResidues, TmpFile, 1) == -1:
                self.DisplayMessage("  ERROR: Could not retrieve list of residues for object/selection '" + self.defaultOption.get() + "'", 2)
                return            
            
            if self.listResidues.count(self.ResiduValue.get()) == 0:
                self.DisplayMessage("  ERROR: The residue entered could not be found in the object/selection '" + self.defaultOption.get() + "'", 2)
                self.EntryResidu.config(bg=self.top.Color_Red)
                return

            self.EntryResidu.config(bg=self.top.Color_White)

        self.DisplayMessage("  Analyzing clefts for object/selection '" + self.defaultOption.get() + "'...", 0)
        
        #TmpFile = '/Users/francisgaudreault/1stp.pdb'
        Command_Line = '"' + self.top.GetCleftExecutable + '" -p "' + TmpFile + '"' + self.Get_Arguments()
        
        # Clear temporary clefts
        self.Btn_Clear_Clicked()

        self.top.ProcessError = False
        self.top.ProcessRunning = True

        self.GetCleftRunning(True)
        
        # Run GetCleft
        StartRun = Start(self, self.queue, Command_Line)
        
    ''' ==================================================================================
    FUNCTION Condition_Update: Tests tab specific conditions to trigger stopping
    ==================================================================================  '''               
    def Condition_Update(self):

        if self.top.ProcessRunning:
            return True
        else:
            return False

    ''' ==================================================================================
    FUNCTION After_Update: Executes tasks when done updating Tkinter
    ==================================================================================  '''               
    def After_Update(self):
        
        # Store clefts and show them
        self.top.Manage.delete_Temp()
        self.top.Manage.store_Temp(self.LastdefaultOption)
        
        nCleft = self.TempBindingSite.Count_Cleft()
        if nCleft > 0:
            self.DisplayMessage("  Stored (" + str(nCleft) + 
                                ") cleft objects from object/selection '" +
                                self.LastdefaultOption + "'", 0)

            self.Display_Temp()
            self.top.Go_Step2()
            self.top.CopySession = False
            self.top.EditSession = False

            self.top.Crop.Reset_Step1()

        else:
            self.DisplayMessage("  No clefts found for object/selection '" +
                                self.LastdefaultOption + "'", 0)

    ''' ========================================================
                 Display all temporary clefts
        ========================================================'''
    def Display_Temp(self):

        self.SetColorList()
        self.DisplayColorChart()
        
        self.Load_Clefts()
        self.Show_Clefts()
        
    ''' ========================================================
                 Gets all arguments for the cmdline
        ========================================================'''
    def Get_Arguments(self):

        Args = ''
        
        # Centralized on a residue
        if self.ResiduValue.get() != '':
            resnumc = self.ResiduValue.get()
            resre = re.search("[A-Z]+", resnumc[0:4])
            res = str(resre.group(0))
            numre = re.search("[0-9]+", resnumc[:-1])
            num = str(numre.group(0))
            chain = str(resnumc[-1])
            while len(res) < 3:
                res = '-' + res
            Args += ' -a ' + res+num+chain+'-'
            
        # Output location
        OutputPath = self.top.GetCleftTempProject_Dir
        if self.OutputFileValue.get() != '':
            OutputPath = os.path.join(OutputPath,self.OutputFileValue.get())
        else:
            OutputPath = os.path.join(OutputPath,self.defaultOption.get())
        
        Args += ' -o "' + OutputPath + '"'
        
        # Number of clefts maximum
        Args += ' -t ' + self.NbCleft.get()
            
        # Size of spheres
        Args += ' -l ' + str(self.MinRadius.get())
        Args += ' -u ' + str(self.MaxRadius.get())
                
        Args += ' -s'

        self.LastdefaultOption = self.defaultOption.get()

        return Args

    ''' ========================================================
                  Toggles the state of the Start button
        ========================================================'''
    def Toggle_defaultOption(self, *args):

        if self.defaultOption.get() != '':
            self.Btn_StartGetCleft.config(state='normal')
        else:
            self.Btn_StartGetCleft.config(state='disabled')

    ''' ==================================================================================
    FUNCTION Btn_RefreshOptMenu_Clicked: Refresh the selections list in the application
                                         with the selections in Pymol 
    ==================================================================================  '''                
    def Btn_RefreshOptMenu_Clicked(self):
        
        if self.PyMOL:
            exc = []
            General_cmd.Refresh_DDL(self.optionMenuWidget, self.defaultOption, exc, None)
    
    ''' ========================================================
                  Welcome message upon frame built
    ========================================================='''
    def Load_Message(self):

        self.DisplayMessage('', 0)
        self.DisplayMessage('  Opened the default menu... ',0)        

    # Disable/enables the whole frames
    def GetCleftRunning(self, boolRun):
        
        if boolRun:
            self.Start_Update()
            self.Disable_Frame()
        else:
            self.End_Update()
            self.Enable_Frame()
    
    ''' ==================================================================================
    FUNCTION DisplayColorChart: Display the color chart in the GetCleft application 
    ================================================================================== '''   
    def DisplayColorChart(self):
        
        nClefts = self.TempBindingSite.Count_Cleft()
        CleftNames = self.TempBindingSite.Get_SortedCleftNames()
        
        self.ChartBar.delete('all')
        
        if nClefts > Color.NBCOLOR:
            nClefts = Color.NBCOLOR
        
        CellWidth = int(self.ChartBar.cget('width')) / nClefts
        
        LeftCoord = 0
        RightCoord = 0
        
        for i in range(0, nClefts):
            
            m = re.search("_sph_(\d+(_pt)?)", CleftNames[i])
            if m:
                text = m.group(1)
                
            if i == (nClefts-1):
                RightCoord = int(self.ChartBar.cget('width'))
            else:    
                RightCoord = LeftCoord + CellWidth
            
            self.ChartBar.create_rectangle(LeftCoord, 0, RightCoord, self.ChartBar.cget('height'),
                                           fill=self.ColorHex[i])
            
            self.ChartBar.create_text((LeftCoord + RightCoord)/2, int(self.ChartBar.cget('height'))/2,
                                      text=text, font=self.top.font_Title_H)
            
            LeftCoord = RightCoord

    ''' ==================================================================================
    FUNCTION Get_CleftPath: Retrieves the default path of the clefts
    ==================================================================================  '''        
    def Get_CleftPath(self):
                
        if self.LastdefaultOption != '':
            TARGETNAME = self.LastdefaultOption.upper()
        else:
            TARGETNAME = self.defaultOption.get().upper()

        CleftPath = os.path.join(self.top.CleftProject_Dir,TARGETNAME)
        
        return CleftPath

    ''' ==================================================================================
    FUNCTION Btn_Load_Clefts: Asks for user to load clefts
    ==================================================================================  '''        
    def Btn_Load_Clefts(self):

        CleftPath = self.Get_CleftPath()
        
        if not os.path.isdir(CleftPath):
            self.DisplayMessage("  Could not find a Cleft folder for your target:", 2)
            self.DisplayMessage("  The default Cleft folder is used.", 2)
        
            CleftPath = self.top.CleftProject_Dir

        
        LoadFiles = tkFileDialog.askopenfilename(filetypes=[('Cleft file','*.nrgclf')],
                                                 initialdir=CleftPath, title='Load cleft file(s)',
                                                 multiple=1)
        
        # LoadFiles can be string instead of list on Windows. here's a workaround
        if self.top.OSid == 'WIN' :
            LoadFiles = self.top.root.master.splitlist(LoadFiles) # allows the normalisation of filelists, namely list of lenght 1 under Windows won't be processed as a string anymore

        if len(LoadFiles) > 0:
        
            TempBindingSite = BindingSite.BindingSite()
            
            for LoadFile in iter(LoadFiles):

                LoadFile = os.path.normpath(LoadFile)
                
                try:
                    in_ = open(LoadFile, 'rb')
                    Cleft = pickle.load(in_)
                    in_.close()
                    
                    TempBindingSite.Add_Cleft(Cleft)
                except:
                    self.top.DisplayMessage("  ERROR: Could not the cleft '" + LoadFile + "'", 1)
                    pass
                
            if TempBindingSite.Count_Cleft() > 0:
                self.Btn_Clear_Clicked()
                self.TempBindingSite = TempBindingSite
                
                self.Display_Temp()
                self.top.Go_Step2()
                
                self.top.CopySession = True
                self.top.EditSession = True
                self.top.Crop.Reset_Step1()

    ''' ==================================================================================
    FUNCTION Btn_Save_Clefts: Asks for user to save clefts
    ==================================================================================  '''        
    def Btn_Save_Clefts(self):
        
        if self.TempBindingSite.Count_Cleft() > 0:
            
            DefaultPath = os.path.join(self.top.CleftProject_Dir,self.LastdefaultOption.upper())
            if not os.path.isdir(DefaultPath):
                os.makedirs(DefaultPath)
            
            SaveFile = tkFileDialog.asksaveasfilename(initialdir=DefaultPath, title='Choose the Cleft base filename',
                                                      initialfile=self.LastdefaultOption)
            
            if SaveFile:

                SaveFile = os.path.normpath(SaveFile)
                
                if DefaultPath not in SaveFile:
                    self.DisplayMessage("  ERROR: The file can only be saved at its default location", 2)
                    return
                
                if glob(SaveFile + "_sph_*.nrgclf"):
                    message = "The Cleft base filename you selected is already taken. " + \
                              "Are you sure you want to overwrite the files?\n" + \
                              "This may result in unexpected errors as the files may be used in saved session."
                
                    answer = tkMessageBox.askquestion("Question",
                                                      message=message,
                                                      icon='warning')
                    if str(answer) == 'no':
                        self.top.DisplayMessage("  The saving of clefts was cancelled.", 2)
                        return
            
                self.Update_TempBindingSite()
                self.top.Manage.save_Temp()
                
                for CleftName in self.TempBindingSite.Get_SortedCleftNames():
                    
                    Cleft = self.TempBindingSite.Get_CleftName(CleftName)
                    #CleftPath = os.path.join(self.top.CleftProject_Dir,Cleft.UTarget)
                    
                    m = re.match('(\S+)(_sph_(\d+)(_pt)?)', CleftName)
                    if m:
                        CleftNamePrefix = m.group(1)
                        CleftNameSuffix = m.group(2)
                    else:
                        continue
                    
                    #if not os.path.isdir(CleftPath):
                    #    os.makedirs(CleftPath)
                    
                    NewCleftNamePrefix = os.path.split(SaveFile)[1]
                    CleftSaveFile = SaveFile + CleftNameSuffix + '.nrgclf'

                    # rename cleft objects in pymol also if renamed
                    if NewCleftNamePrefix != CleftNamePrefix:
                        
                        try:
                            cmd.set_name(CleftName, NewCleftNamePrefix + CleftNameSuffix)
                        except:
                            self.top.DisplayMessage("  ERROR: Failed to rename cleft '" + Cleft.CleftName + "'", 2)
                            continue

                    Cleft.CleftName = NewCleftNamePrefix + CleftNameSuffix
                    
                    try:
                        out = open(CleftSaveFile, 'wb')
                        pickle.dump(Cleft, out)
                        out.close()
                    
                        #self.top.DisplayMessage("  Successfully saved '" + CleftSaveFile + "'", 0)
                    except:
                        self.top.DisplayMessage("  ERROR: Could not save binding-site '" + CleftSaveFile + "'", 1)
                        continue
                                                        
            else:
                self.top.DisplayMessage("  No clefts to save.", 2)
    
    ''' ==================================================================================
    FUNCTION Load_Clefts: Loads the list of temp clefts
    ==================================================================================  '''        
    def Load_Clefts(self):
            
        auto_zoom = cmd.get("auto_zoom")
        cmd.set("auto_zoom", 0)
        
        # for Cleft in self.TempBindingSite.listClefts:
        for CleftName in self.TempBindingSite.Get_SortedCleftNames():
                Cleft = self.TempBindingSite.Get_CleftName(CleftName)
                try:
                    cmd.load(Cleft.CleftFile, Cleft.CleftName, state=1)
                    cmd.refresh()
                    
                    if Cleft.Partition and Cleft.PartitionParent != None and \
                            General_cmd.object_Exists(Cleft.PartitionParent.CleftName):
                        
                        General_cmd.Oscillate(Cleft.PartitionParent.CleftName, 0.0)
                except:
                    self.top.DisplayMessage("  ERROR: Failed to load cleft object '" + Cleft.CleftName + "'", 2)
                    continue
                    
        cmd.set("auto_zoom", auto_zoom)
        
    ''' ==================================================================================
    FUNCTION Update_TempBindingSite: Update cleft object with only those undeleted in PyMOL
    ==================================================================================  '''                 
    def Update_TempBindingSite(self):
        
        self.TempBindingSite.listClefts = \
            [ Cleft for Cleft in self.TempBindingSite.listClefts \
                if General_cmd.object_Exists(Cleft.CleftName) ]
                
    ''' ==================================================================================
    FUNCTION SetColorList: Reset the color lists
    ==================================================================================  '''        
    def SetColorList(self):
        
        nColor = self.TempBindingSite.Count_Cleft()
        
        if nColor > Color.NBCOLOR:
            nColor = Color.NBCOLOR
            
        self.ColorList = Color.GetHeatColorList(nColor, False)
        self.ColorHex = Color.GetHeatColorList(nColor, True)
        
    ''' ==========================================================
    SetPartitionColor: sets a new color to the partition based on its parent
    ==========================================================='''           
    def SetPartitionColor(self, Sel):
        
        try:
            mycolors = {'colors': []}
            cmd.iterate( Sel, 'colors.append(color)', space=mycolors)

            for color in mycolors['colors']:
                one = list( cmd.get_color_tuple(color) )
                break

            for i in range(0,3):
                if one[i] <= 0.80:
                    one[i] += 0.20
                else:
                    one[i] -= 0.20
            
            cmd.set_color(self.PartitionColor, one)
            partition_rgb = General.one_to_rgb(one)
            
        except:
            return tuple()

        return tuple(partition_rgb)
    
    ''' ==================================================================================
    FUNCTION Show_Clefts: Shows the 'Cleft' object a cavity
    ================================================================================== '''   
    def Show_Clefts(self):
        
        i = 0
        for CleftName in self.TempBindingSite.Get_SortedCleftNames():
            Cleft = self.TempBindingSite.Get_CleftName(CleftName)
            
            try:
                cmd.hide('everything', Cleft.CleftName)
                cmd.refresh()

                cmd.color(self.ColorList[i], Cleft.CleftName)
                cmd.refresh()
                
                cmd.show('surface', Cleft.CleftName)
                cmd.refresh()
                
                Cleft.Color = self.ColorHex[i]
                
                i += 1
            except:
                self.DisplayMessage("  ERROR: Could not display cleft object '" + Cleft.CleftName + "'", 2)
                continue
                    
    ''' ==================================================================================
    FUNCTION Btn_DownloadPDB_Clicked: Download a PDB from the internet and display the
                                      result in Pymol 
    ==================================================================================  '''    
    def Btn_DownloadPDB_Clicked(self):       

        PdbCode = self.FetchPDB.get()
        
        try:            
            if self.PyMOL:
                cmd.fetch(PdbCode, **{'async': 0})
                cmd.refresh()
        except:
            self.DisplayMessage('  You entered an invalid PDB code.', 1)
            
        self.FetchPDB.set('')
