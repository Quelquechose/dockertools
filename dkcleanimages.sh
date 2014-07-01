#!/bin/bash
docker.io images --no-trunc| grep none | awk '{print $3}' | xargs -r docker.io rmi
