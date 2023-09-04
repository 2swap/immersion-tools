#!/bin/bash

# Read the config file line by line, splitting fields using tab as the delimiter
while IFS=$'\t' read -r url disk_location extra_args; do
    # Skip lines that start with a '#' (comments)
    [[ $url =~ ^#.* ]] && continue
        
    # Echo information about the current synchronization
    echo "Syncing URL $url at disk location $disk_location, with extra args $extra_args"
    
    # Call yt-dlp with provided arguments and options
    yt-dlp --all-subs $extra_args --download-archive archive.txt --cookies-from-browser chrome -o "$disk_location" "$url"
done <config.tsv
