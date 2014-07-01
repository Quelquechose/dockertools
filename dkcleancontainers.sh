#!/bin/bash
docker.io ps -a --no-trunc | grep 'Exit' | awk '{print $1}' | xargs -r docker.io rm
