RM = rm -fr
SRC = PyCmd.py InputState.py DirHistory.py common.py completion.py console.py

dist: clean $(SRC)
	python setup.py py2exe
	mv dist PyCmd
	cp NEWS.txt README.txt PyCmd
	zip -r PyCmd.zip PyCmd

.PHONY: clean
clean:
	$(RM) $(SRC:%.py=%.pyc)
	$(RM) -fr build PyCmd
	$(RM) -f PyCmd.zip
