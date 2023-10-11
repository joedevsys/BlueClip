# BlueClip
Python program to sync clipboards over Bluetooth serial ports. Large-button UI for accessibility.

### Introduction
Blueclip synchronises clipboards over bluetooth. Sync can be manual or automatic. If auto sync occurs when when the clipboard changes on one computer causing the change is sent to the clipboard on the other computer and so  the programs can be minimised in the background and synchronisation will happen with no further user action. 

Multiple pairings can be set up but only one is chosen as the active one at any given time. A typical setup would be a one-to-many arrangement with the central device choosing which target to send to, one at a time.

Large buttons are displayed for easy accessibility and for people who use eyegaze control.

Why bluetooth sync? There are many utilities to sync clipboards over local area networks but these suffer from a number of disadvantages. If devices are on different subnets (e.g. one wired and one wireless) it can be hard to configure connections through firewalls & routers. Cloud based commercial solutions introduce other problems or can be too complex as they add other functionality.  The Windows operating system has a built-in clipboard sync feature but this requires signing into a Microsoft Account which isn’t always desirable and not possible on some kiosk-style devices. Bluetooth allows repeatable local fixed connections to be pre-configured which are independent of internet connectivity and not tied to network login accounts etc.

## Installation
Copy all the files to a suitable location (e.g. c:/program files/BlueClip/) and create a shortcut for the .exe file if desired. Blueclip runs from any location but keep all its files together in one folder.

## Configuration (Windows10)
![image](https://github.com/joedevsys/BlueClip/assets/84750746/e75b7dc2-550e-4ee7-b562-24d9d3cdfdf8)

Create a Bluetooth pairing between your devices in the normal way
Setup bluetooth serial connections and edit the config file on each machine as follows:

**On Machine #1:**   _[This machine becomes a Listener waiting for connection]_
	
 Bluetooth Settings|More Bluetooth Options-->comm ports tab: ADD, Incoming connection
	Take note of virtual comm port number.
	Now edit BlueClip.ini and set the hostname, port and other options as desired.
	(N.B. ports entry can be multiline but typically the listener will only have one line.)
```
	e.g	[DEFAULT]
		hostname = Machine1    	←the name of this machine
		autopaste = 1
		[PORTS]
		ports=
			com3 “LISTENING”	←the port this machine is listening on
```

**On Machine #2:**  _[This machine becomes the Caller that calls the Listener]_
	
 Bluetooth Settings|More Bluetooth Options-->comm ports tab: ADD, Outgoing connection, 	Browse to target = Machine #1 Port 3    	 ←the target machine & it’s port
	Take note of new virtual comm port number just created (this might be different to 	Machine#1’s port).
	Now edit BlueClip.ini and set the hostname, port and other options as desired.
	(Note the ports entry can be multiline as this machine can call multiple Listeners. Each line has the outgoing port just created on this machine but the name is the name of the target 	machine it connects to).
```
	e.g. 	[DEFAULT]
		hostname = Machine2		←the name of this machine
		autopaste = 1			←auto sync whenever clipboard changes
		autominimise=1			←auto minimise BlueClip once connected
		[PORTS]
		ports=
			com6 “Machine1”	←list of this machine’s ports and names
			com7 “Machine3”  	 of the targets they connect to 
```

## Configuration (Linux)
To Be Done...

## Usage

- Launch BlueClip.exe and it will keep trying to connect to the other machine. Once blueclip is launched on the other machine they will automatically connect. 
- If multiple machines are configured then clicking on change connection will try and connect ot the next target. It will remember this new target and try and reconnect next time it’s launched.
- If the connection is interupted blueClip will keep trying to reconnect.
- Once connected if autominimise is enabled in the .INI file the app will minimise. 
- If autopaste is enabled then every time the clipboard changes it will be synchronised to the other machine. N.B. If for some reason the synchronisation doesn’t complete then repeating the same Copy again and again will not succeed. You will need to Copy something different to trigger another sync, and then go back and try and Copy the thing you originally wanted.
- If autopaste is disabled synchronisation only occurs when you click “Paste Now” (=paste to the other machine’s clipboard).


## Developer

Setup
```
pip install pyserial
pip install pyperclip
pip install tkinter
pip install pyinstaller --->(for compilation to .exe)
```

Compile for windows
```
cd \<source directory\>

pyinstaller --onefile \<source filename\>    --->.exe produced from filename *.py will run with console active. Filename *.pyw produces .exe with no console output. make sure you're in the source directory!

pyinstaller --onefile -i blueclip.ico "blueclip.pyw"   --->blueclip.exe normal operation

copy blueclip.pyw blueclip.py
pyinstaller --onefile -i blueclip.ico "blueclip debug.py"    --->blueclip debug.exe runs with additional console
```


