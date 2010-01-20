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

SRC = PyCmd.py InputState.py DirHistory.py common.py completion.py console.py fsm.py
SRC_TEST = common_tests.py

dist: clean $(SRC)
	python setup.py py2exe
	$(MV) dist PyCmd
	$(CP) NEWS.txt README.txt PyCmd
	$(ZIP) -r PyCmd.zip PyCmd

.PHONY: clean
clean:
	$(RM) $(SRC:%.py=%.pyc)
	cd tests && $(RM) $(SRC_TEST:%.py=%.pyc) && $(RM) __init__.pyc
	$(RM) -r build PyCmd
	$(RM) PyCmd.zip
