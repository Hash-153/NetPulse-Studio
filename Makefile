.PHONY: all install build run test clean docker-build docker-up

all: build test

install:
	pip install -r requirements.txt

build:
	python -m py_compile server/main.py

run:
	python server/main.py --host 127.0.0.1 --port 8080

test:
	python server/tests/run_all_tests.py

docker-build:
	docker build -t netpulse:latest .

docker-up:
	docker-compose up -d

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
