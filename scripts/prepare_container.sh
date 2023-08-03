#!/bin/bash

## resolve folder of this script, following all symlinks,
## http://stackoverflow.com/questions/59895/can-a-bash-script-tell-what-directory-its-stored-in
SCRIPT_SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SCRIPT_SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  SCRIPT_DIR="$( cd -P "$( dirname "$SCRIPT_SOURCE" )" && pwd )"
  SCRIPT_SOURCE="$(readlink "$SCRIPT_SOURCE")"
  # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
  [[ $SCRIPT_SOURCE != /* ]] && SCRIPT_SOURCE="$SCRIPT_DIR/$SCRIPT_SOURCE"
done
readonly SCRIPT_ORIGIN="$( cd -P "$( dirname "$SCRIPT_SOURCE" )" && pwd )"
	readonly REPO_DIR=`dirname $SCRIPT_ORIGIN`
readonly REPO_NAME=`basename $REPO_DIR`

set -exo pipefail

IS_NESTED=$1
## cleaning any existing podman images and containers
podman rmi -a -f
podman rm -a -f
podman ps -all
podman images

## create local workspace
rm -rf $SCRIPT_ORIGIN/../local_workspace
mkdir $SCRIPT_ORIGIN/../local_workspace
CONT_WORKSPACE=$SCRIPT_ORIGIN/../local_workspace

## copy files necessary for benchmarking
cd $CONT_WORKSPACE
cp -r $SCRIPT_ORIGIN $CONT_WORKSPACE
cp -r /mnt/shared/TckScripts $CONT_WORKSPACE
cp -r /mnt/shared/testsuites $CONT_WORKSPACE

if [ $IS_NESTED == True ]; then
  FEDORA_VERSION=$(cat $SCRIPT_ORIGIN/../config | grep ^NESTED= | sed "s/.*=//")
else
  FEDORA_VERSION=$(cat $SCRIPT_ORIGIN/../config | grep ^MAINVM= | sed "s/.*=//")
fi

## create the dockerfile for creating the base 
preparation_dockerfile=preparation_dockerfile
echo "FROM $FEDORA_VERSION" >> $preparation_dockerfile
echo 'RUN dnf -y install bc xz /usr/bin/scp which /usr/bin/find && dnf clean all' >> $preparation_dockerfile
echo "RUN mkdir /test || true" >> $preparation_dockerfile
echo 'RUN mkdir /test/scripts || true' >> $preparation_dockerfile
echo "RUN mkdir /mnt/shared || true" >> $preparation_dockerfile
echo "RUN mkdir /mnt/shared/testsuites || true" >> $preparation_dockerfile
echo "RUN mkdir /mnt/shared/TckScripts || true" >> $preparation_dockerfile
echo "RUN mkdir /results || true" >> $preparation_dockerfile
echo "RUN ls -l /" >> $preparation_dockerfile

echo "COPY TckScripts /mnt/shared/TckScripts" >> $preparation_dockerfile
echo "COPY scripts /test/scripts" >> $preparation_dockerfile
#improve so only the current benchmark gets copied?
echo "COPY testsuites /mnt/shared/testsuites" >> $preparation_dockerfile

echo "RUN ls -l /mnt/shared/testsuites" >> $preparation_dockerfile
echo "RUN ls -l /" >> $preparation_dockerfile
echo "RUN pwd " >> $preparation_dockerfile

podman build --tag preparation-cont -f ./$preparation_dockerfile 

echo finished-preparing-container

