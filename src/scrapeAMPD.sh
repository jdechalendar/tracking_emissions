#!/bin/bash

# Bash script to download the AMPD files

url="ftp://newftp.epa.gov/DMDnLoad/emissions/hourly/monthly/"
year=2016
target="$DATA_PATH/raw/AMPD/${year}"
mkdir -p $target

# list files to download
for i in $( curl -l "${url}${year}/" );
do
    echo $i
    echo "${target}${i}.csv"
    echo "${target}${i:0:-4}.csv"
    if [ ! -f "${target}${i:0:-4}.csv" ]; then
        echo "Adding ${i}...";
        full_url="${url}${year}/${i}"
        echo "Downloading ${full_url}..."
        curl -o "${target}tmp.zip" "${full_url}"
        echo "Unzipping..."
        unzip -n "${target}tmp.zip" -d "$target"
    else
        echo "${i} already exists!";
    fi
done;
