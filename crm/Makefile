# CRM sub-project Makefile
# Windows note: if `make` is unavailable, run the raw commands shown in each target comment.

BINARY   := bin/crm-server
MAIN     := ./app/cmd/server
DATA_DIR := ./data
DB_PATH  := $(DATA_DIR)/crm.db
MIGRATE  := migrate

.PHONY: build run migrate-up migrate-down sqlc vet clean

## build: compile static binary (CGO_ENABLED=0, pure-Go SQLite)
##   raw: CGO_ENABLED=0 go build -o bin/crm-server ./app/cmd/server
build:
	CGO_ENABLED=0 go build -o $(BINARY) $(MAIN)

## run: run the server directly (no pre-built binary needed)
##   raw: CGO_ENABLED=0 CRM_DATA_DIR=./data CRM_PORT=8090 go run ./app/cmd/server
run:
	CGO_ENABLED=0 go run $(MAIN)

## migrate-up: apply pending migrations via embedded Go runner
##   raw: CGO_ENABLED=0 go run ./app/cmd/migrate up
migrate-up:
	CGO_ENABLED=0 go run ./app/cmd/migrate up

## migrate-down: roll back one migration step via embedded Go runner
##   raw: CGO_ENABLED=0 go run ./app/cmd/migrate down
migrate-down:
	CGO_ENABLED=0 go run ./app/cmd/migrate down

## sqlc: generate query layer from SQL files
##   raw: cd app && sqlc generate
sqlc:
	cd app && sqlc generate

## vet: run go vet
##   raw: go vet ./...
vet:
	go vet ./...

## clean: remove compiled binary and SQLite runtime files
clean:
	rm -f $(BINARY)
	rm -f $(DATA_DIR)/*.db $(DATA_DIR)/*.db-wal $(DATA_DIR)/*.db-shm
