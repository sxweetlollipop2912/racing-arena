cli:
	python client/client.py
ser:
	python server/server.py

build-cli:
	rm -rf dist
	mkdir -p dist/client
	cp -r client/assets dist/client
	pyinstaller -n client-binary -w -F -p ./client/ --add-data ./dist/client/assets/:client/assets/ client/client.py
build-ser:
	pyinstaller -n server-binary -F -p ./server/ server/server.py