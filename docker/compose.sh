#!/bin/bash

usage() {
  echo "Usage: $0 todo..." 1>&2
}

exit_abnormal() {
  usage
  exit 1
}

build() {
  cat ./*/requirements.txt >./all-requirements.txt
  docker-compose build $1
}

up() {
  docker-compose up -d $1
}

stop() {
  docker-compose stop $1
}

while getopts "bus" options; do
  case "${options}" in
  b)
    build $OPTARG
    ;;
  u)
    up $OPTARG
    ;;
  s)
    stop $OPTARG
    ;;
  *)
    exit_abnormal
    ;;
  esac
done

exit 0
