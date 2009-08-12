RM = rm -fr
SRC = PyCmd.py InputState.py DirHistory.py common.py completion.py console.py fsm.py
SRC_TEST = common_tests.py

dist: clean $(SRC)
	python setup.py py2exe
	mv dist PyCmd
	cp NEWS.txt README.txt PyCmd
	zip -r PyCmd.zip PyCmd

.PHONY: clean
clean:
	$(RM) $(SRC:%.py=%.pyc)
	cd tests && $(RM) $(SRC_TEST:%.py=%.pyc) && $(RM) __init__.pyc
	$(RM) -fr build PyCmd
	$(RM) -f PyCmd.zip
