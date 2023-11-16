#import serial
import tkinter
from tkinter import *
import serial.threaded
import time
import platform
import sys
import pyclip
import getopt
import traceback
import configparser
import inspect, os.path
import re
from winotify import Notification
from tendo import singleton




def get_params(argv):
    global config
    global cfgfile
    global portlist
    global lastport
    global immediate
    global auto
    global autominimise
    global name
    # try:
    #     opts, args = getopt.getopt(argv, "hip:i:a:n:", ["port=", "immediate=", "auto", "name"])
    # except getopt.GetoptError:
    #     print('ClipSerial.py -p <port> -i <immediate> -a <autopaste> -n <name>')
    #     sys.exit(2)
    # for opt, arg in opts:
    #     if opt == '-h':
    #         print('ClipSerial.py -p <port> -i <immediate> -a <autopaste> -n <name>')
    #         sys.exit()
    #     elif opt in ("-i", "--immediate"):
    #         immediate = (arg != 0) or (arg != 'false') or (arg != 'FALSE')
    #     elif opt in ("-p", "--port"):
    #         port = arg
    #     elif opt in ("-a", "--autopaste"):
    #         auto = (arg != 0) or (arg != 'false') or (arg != 'FALSE')
    #     elif opt in ("-n", "--name"):
    #         name = arg
    cfgfile=get_my_path() +'BlueClip.ini'
    config = configparser.ConfigParser()
    print ("Reading config file "+cfgfile)
    config.read(cfgfile)
    name = config.get('DEFAULT', 'hostname')
    auto = config.getboolean('DEFAULT', 'autopaste',fallback=False)
    immediate = config.getboolean('DEFAULT', 'immediate',fallback=False)
    autominimise = config.getboolean('DEFAULT', 'autominimise',fallback=True)
    portlist = config.get('PORTS', 'ports',fallback=portlist)
    lastport = config.getint('PORTS', 'lastport',fallback=0)
    print('    Portlist ' + portlist)
    print('    Last port ' +str(lastport))
    print('    Auto ' + str(auto))
    print('    Paste immediately ' + str(immediate))
    print('    Auto minimise ' + str(autominimise))
    print('    Name ' + name)


def set_config(data):
    global config
    global cfgfile
    f=open(cfgfile,'w')
    config.set('PORTS','lastport',str(data))
    config.write(f)
    f.close()


def get_my_path():
    filename = inspect.getframeinfo(inspect.currentframe()).filename
    path = os.path.dirname(os.path.abspath(filename))
    return path+'/'


def notify(title,data):
    if platform.system()=='Windows':
      toast = Notification(app_id="BLUE CLIP",
                     title=title,
                     msg=data,
                     icon=get_my_path()+"BlueClip.ico")  
      toast.show()



#comms-----------------------------------------------------------------------------------------------


class CommsHandler(serial.threaded.LineReader):
    tk_listener = None

    def connection_made(self, transport):
        if self.tk_listener is None:
            raise Exception("tk_listener must be set before initialising the connection!")
        super(CommsHandler, self).connection_made(transport)
        sys.stdout.write('port opened\n')
        self.TERMINATOR = b'\0'

    def handle_line(self, data):
        # Execute our callback in tk
        self.tk_listener.window.after(0, self.tk_listener.on_data, data)

    def connection_lost(self, exc):
        if exc:
            #traceback.print_exc(exc)
            print(exc)
        sys.stdout.write('Comms Handler closed\n')
        self.tk_listener.window.abandonConnection.set(True)




#logic --  performed in the tk thread ---------------------------------------------------------------

class clipSharer():
    name = ''
    targetPort = ''
    targetPortName = ''
    receivedPortName=''
    ser = None
    myReader = None
    window= None
    connected = False
    pingcount=0
    closing=False
    PINGLIMIT=2

    def on_data(self, data):
        intext = repr(data)
        sys.stdout.write('received: {}\n'.format(intext))
        if len(data) > 0:
            if data[0] == 'C':
                self.receiveClip(data[1:])
            if data[0] == '?':
                self.replyPing()
            if data[0] == 'P':
                self.receivePingResult(data[1:])
    
    
    def sendCommand(self, data):
        try:
            if (self.ser is not None):
               if self.ser.is_open:
                   if self.ser.cts:
                      self.myReader.write_line(data)
                      return True
                   else:
                      sys.stdout.write('Send fail: remote not ready\n')
                      if self.pingcount>=self.PINGLIMIT:
                          raise ConnectionError
                      else:
                          return True
               else:
                   sys.stdout.write('Send fail: port not open\n')
                   self.window.abandonConnection.set(True)
                   raise ConnectionError
            else:
                sys.stdout.write('Send fail: port not ready\n')
                self.window.abandonConnection.set(True)
                raise ConnectionError
        except Exception as e:
              print (e)
              self.window.showStatus(False,"Lost connection",True)
              self.window.abandonConnection.set(True)
              return False
    
    
    def sendClip(self, data):
        self.sendCommand('C' + data)
    
    
    def receiveClip(self, data):
        sys.stdout.write('Clipboard ' + data)
        if len(data) > 0:
            pyclip.copy(data)
            self.window.prevclip = data
            notify("Clip Received","")
    
    
    def sendPing(self):
        sys.stdout.write('Send ping\n')
        if self.sendCommand('?'):
           self.window.after(3813, self.checkPing)
        self.pingcount = self.pingcount+1
    
    
    def checkPing(self):
        sys.stdout.write('Check ping '+str(self.pingcount)+'\n')
        if self.pingcount==0 and not self.window.abandonConnection.get():  #ok
            self.connected=True
            self.window.showStatus(True,"Connected to " + self.receivedPortName,True)
        elif self.pingcount>0 and self.pingcount<self.PINGLIMIT:  #missed response
            if self.connected:
                self.window.showStatus(True,"Connected to " + self.receivedPortName+"\n?",False)
            sys.stdout.write("  lost pings " + str(self.pingcount)+'\n')
        else:  #fail
            self.connected=False
            self.window.showStatus(False,"No Response",True)
            sys.stdout.write("  lost pings " + str(self.pingcount)+'\n')
        self.window.after(1200, self.sendPing)
        #self.sendPing()
    
    def replyPing(self):
        sys.stdout.write('Reply ping\n\n')
        self.sendCommand('P' + self.name)
    
    
    def receivePingResult(self, data):
        if len(data) > 0:
            self.receivedPortName=data
            self.window.showStatus(True,"Connected to " + self.receivedPortName,False)
            self.pingcount = 0
    
    
    def autoPaste(self):
        # sys.stdout.write('Auto check\n')
        if self.window.auto:
            if self.window.autominimise and self.connected:
                self.minimise()
            currentclip = pyclip.paste(text=True)
            if currentclip != self.window.prevclip:
                sys.stdout.write('Paste Auto\n')
                self.window.prevclip = currentclip
                self.sendClip(currentclip)
            self.window.after(5000, self.autoPaste)

    
    def minimise(self):
        self.window.iconify()
        self.window.autominimise=False   #don't keep minimising in case user wishes to override
   
    
    def makeConnection(self):
        self.ser=None
        reason=''
        CommsHandler.tk_listener=self
        self.connected = False
        self.pingcount=0
        self.closing=False
        sys.stdout.write('makeConnection '+self.targetPortName+'\n')
        try:
          self.ser = serial.serial_for_url(self.targetPort, baudrate=9600, timeout=1)
        except serial.SerialException  as se:
            print(se)
            m=re.search(r'\(([0-9]+),.*,\s([0-9]+)\)',str(se))
            errno=int(m.group(1))
            winerr=int(m.group(2))
            if errno == 2:
                reason="Can't find local port"
            elif errno==22:
                if winerr==1168:
                  reason='Remote BT error'
                elif winerr==1256:
                  reason='Remote App not found'
                elif winerr==121:
                  reason='Remote Bluetooth not responding'
                else:
                  reason='Port error '+str(errno)+'.'+str(winerr)
                #reason=reason+' ' + self.targetPort
            else:
                reason='Port Error '+str(errno)+'.'+str(winerr)
            sys.stdout.write(reason+' ' + self.targetPort+ ".\n")
            self.ser = None
        except exception as e:
            print(e)
            reason=str(e)
            self.ser = None
        if (self.ser is not None):
            if (self.ser.is_open):
                self.ser.flush()
                self.ser.reset_input_buffer()
                self.ser. reset_output_buffer()
                with serial.threaded.ReaderThread(self.ser, CommsHandler) as self.myReader:
                    if self.window is None:  #immediate:
                        time.sleep(2)
                        sys.stdout.write('Paste immediate\n')
                        cmd = pyclip.paste(text=True)
                        self.sendCommand(cmd)
                        time.sleep(2)
                    else:
                        self.window.showStatus(False,"Bluetooth Connected\nWaiting for response",False)
                        if self.window.auto:
                            self.window.prevclip = pyclip.paste(text=True)
                            self.window.after(5000, self.autoPaste)
                        self.window.after(4213, self.sendPing)
                        self.window.abandonConnection.set(0)
                        self.window.wait_variable(self.window.abandonConnection)
            else:
                #ser has been created without exception so if can't open maybe locked, in use etc???
                sys.stdout.write("Can't open port " + self.targetPort + ".\n")
        else:
            #exception, unable to create ser 
            #self.window.showStatus(False,reason+self.targetPortName,False)
            pass
        if not self.closing:
            self.window.showStatus(False,"Trying to connect\n"+reason,True)
        sys.stdout.write('makeConnection Exit\n')
        self.window.after(5000,self.makeConnection)




        

#gui------------------------------------------------------------------------------------------

class MainWindow(Tk):
    auto = False
    autominimise = False
    process=None

    status = None
    btnAuto = None
    btnPaste = None
    btnConnect=None
    labelTarget=None

    target = 0
    abandonConnection = False
    prevclip= ""
    connectionNotificationSent=False


    def __init__(self, auto, autominimise, name,lastport):
        super().__init__()
        self.target=lastport
        self.auto = auto
        self.autominimise = autominimise
        x = int(self.winfo_screenwidth()) - 200
        self.geometry('200x500+' + str(x) + '+0')
        self.resizable(False, False)
        self.wm_title("BlueClip")
        try:
            self.iconbitmap('./BlueClip.ico')
        except:
            pass
        frame = Frame(self)
        frame.pack(side=TOP, padx=2, pady=5)
        #label1=Label(frame, width=25, height=1,text="Target:  ")
        #label1.pack(side=TOP)
        self.labelTarget=Label(frame, width=25, height=1,text="Connect to: "+destinations[self.target],font=("Arial", 12) )
        self.labelTarget.pack(side=TOP,padx=5, pady=5)
        self.status = Label(frame, width=25, height=4, text="Connecting Bluetooth\n"+ports[self.target], bg='white')
        self.status.pack(side=TOP, padx=5, pady=5)
        #self.status.bind("<Button-1>", self.clickStatus)
        self.abandonConnection = IntVar()
        self.abandonConnection.set(False)
        if len(ports)>1:
            self.geometry('200x600+' + str(x) + '+0')
            self.btnConnect=Button(self, text="Change Connection\nto "+destinations[(self.target+1)%len(ports)], width=15,height=5, command=self.clickBtnConnect)
            self.btnConnect.pack(side=TOP, pady=5)
        self.btnPaste = Button(self, text="Paste Now", width=15, height=4, command=self.clickBtnPaste)
        self.btnPaste.pack(side=TOP, padx=5, pady=4)
        self.btnPaste["state"] = DISABLED
        self.btnAuto = Button(self, text="Auto", width=15, height=4, command=self.clickBtnAuto)
        self.btnAuto.pack(side=TOP, padx=5, pady=5)
        self.btnAuto["state"] = DISABLED
        btnMinimise = Button(self, text="Minimise", width=15, height=4, command=self.iconify)
        btnMinimise.pack(side=TOP, padx=5, pady=5)
        btnQuit = Button(self, text="Quit", width=15, height=4, command=self.on_closing)
        btnQuit.pack(side=TOP, padx=5, pady=5)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.process = clipSharer()
        self.process.name = name
        self.process.window=self
        i = min(self.target, len(ports) - 1)
        self.process.targetPort=ports[i]
        self.process.targetPortName=destinations[i]
        self.after(5000, self.process.makeConnection)


    def clickBtnConnect(self):
         sys.stdout.write('Status Clicked\n')
         self.abandonConnection.set(True)
         self.target=(self.target + 1) % len(ports)
         #i = min(self.target, len(ports) - 1)
         self.process.targetPort = ports[self.target]
         self.process.targetPortName = destinations[self.target]
         self.status.config(text="Disconnecting")
         self.btnConnect.config(text= "Change Connection\nto " + destinations[(self.target+1)%len(ports)] )
         self.labelTarget.config(text= "Connect to " + destinations[(self.target)] )
         set_config(self.target)
         #altering abandonConnection causes tk's Window.wait_variable to terminate and closes any currently open port.
         #it also changes the index into the list of ports in ports read to open the next port


    def clickBtnPaste(self):
        sys.stdout.write('Paste Button\n')
        if self.process is not None:
            clip = pyclip.paste(text=True)
            self.process.sendClip(clip)


    def clickBtnAuto(self):
        self.auto = not self.auto
        if self.auto:
            self.prevclip = pyclip.paste(text=True)
            if self.process is not None:
                self.after(5000, self.process.autoPaste)
                self.btnAuto.config(bg='green')
                self.btnPaste["state"] = DISABLED
                if autominimise:
                    self.iconify()
        else:
            self.btnAuto.config(bg='lightgray')
            self.btnPaste["state"] = NORMAL


    def on_closing(self):
        self.abandonConnection.set(False)  # trigger connection to close too
        time.sleep(0.1)
        self.destroy()
        self.process.closing=True
        exit()


    def showStatus(self,connected,msg,sendnotification):
        if connected: 
                self.status.config(text=msg, bg='green')
                self.btnPaste["state"] = NORMAL
                self.btnAuto["state"] = NORMAL
                if self.auto:
                    self.btnAuto.config(bg='green')
                else:
                    self.btnAuto.config(bg='lightgray')
                if sendnotification and not self.connectionNotificationSent:
                    notify("Connected",self.process.receivedPortName)
                    self.connectionNotificationSent=True
                try:
                    self.iconbitmap('./BlueClipConnected.ico')
                except:
                    pass
        else:  #fail
                self.status.config(text=msg, bg='white')
                self.btnPaste["state"] = DISABLED
                self.btnAuto["state"] = DISABLED
                self.btnAuto.config(bg='lightgray')
                if sendnotification and self.connectionNotificationSent:
                    notify("Lost Connection",self.process.receivedPortName)
                    self.connectionNotificationSent=False
                try:
                    self.iconbitmap('./BlueClipNotConnected.ico')
                except:
                    pass





#main--------------------------------------------------------------------------------------------


# if __name__ == "__main__":
#Get parameters or config options
try:
  me = singleton.SingleInstance() # will sys.exit(-1) if other instance is running
  config=None
  portlist = '/dev/rfcomm0 "p0"\n/dev/rfcomm3 "p3"'  # 'com3'
  lastport=0
  immediate = False
  auto = False
  autominimise = True
  name = platform.node()
  get_params(sys.argv[1:])
  portlist=re.split('\s+"|"\s?\n',portlist.rstrip('"').lstrip(' ').lstrip('\n'))
  ports=portlist[0::2]
  destinations=portlist[1::2]
  print (ports)

  if immediate:
    #N.B. if using immediate only set one port in ini file as no way to select which port.
    makeConnection(None)
  else:
    window=MainWindow(auto, autominimise, name,lastport)
    window.mainloop()
except:
  pass
