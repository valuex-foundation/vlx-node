.PHONY: build up down logs status test package
build:
	bash vlx-node.sh build
up:
	bash vlx-node.sh start
down:
	bash vlx-node.sh stop
logs:
	bash vlx-node.sh logs
status:
	bash vlx-node.sh status
test:
	python3 -m unittest discover -s tests
package:
	python3 scripts/package-public.py
