#
# Makefile for creating a PyCmd.zip binary distribution
# Requires:
#	* MinGW (make, rm, cp etc) and python in the %PATH%
#	* py2exe and pywin32 installed in the Python 
#
# Author: Horea Haitonic
#
RM = rm -f
CP = cp
MV = mv
ZIP = zip
SHELL = cmd

SRC = PyCmd.py InputState.py DirHistory.py common.py completion.py console.py fsm.py
SRC_TEST = common_tests.py

PYTHONHOME_W32 = C:\Python27
PYTHONHOME_W64 = C:\Python27-amd64

PYTHON_W32 = (set PYTHONHOME=$(PYTHONHOME_W32)) && "$(PYTHONHOME_W32)\python.exe"
PYTHON_W64 = (set PYTHONHOME=$(PYTHONHOME_W64)) && "$(PYTHONHOME_W64)\python.exe"

ifndef BUILD_INFO
	BUILD_INFO = $(shell echo %DATE%| sed "s/...\ \(..\)\/\(..\)\/\(....\)/\3\1\2/")
endif

.PHONY: all
all: 
	$(MAKE) clean
	$(MAKE) dist_w32 
	$(MAKE) clean
	$(MAKE) dist_w64

dist_w32: clean $(SRC)
	echo build_info = '$(BUILD_INFO)' > buildinfo.py
	$(PYTHON_W32) setup.py build
	$(MV) build\exe.win32-2.7 PyCmd
	$(CP) NEWS.txt README.txt PyCmd
	$(ZIP) -r PyCmd-$(BUILD_INFO)-w32.zip PyCmd

dist_w64: clean $(SRC)
	echo build_info = '$(BUILD_INFO)' > buildinfo.py
	$(PYTHON_W64) setup.py build
	$(MV) build\exe.win-amd64-2.7 PyCmd
	$(CP) NEWS.txt README.txt PyCmd
	$(ZIP) -r PyCmd-$(BUILD_INFO)-w64.zip PyCmd

.PHONY: clean
clean:
	$(RM) buildinfo.*
	$(RM) $(SRC:%.py=%.pyc)
	cd tests && $(RM) $(SRC_TEST:%.py=%.pyc) && $(RM) __init__.pyc
	$(RM) -r build PyCmd
