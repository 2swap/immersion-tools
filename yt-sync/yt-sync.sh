#!/bin/bash

# Common prefix and tail for disk location
common_prefix='/media/swap/primary/'
common_tail='/%(upload_date>%Y-%m-%d)s - %(title)s.%(ext)s'

# Read the config file line by line, splitting fields using tab as the delimiter
while IFS=$'\t' read -r url disk_location extra_args || [[ -n "$url" ]]; do
    # Skip lines that start with a '#' (comments)
    [[ $url =~ ^#.* ]] && continue

    # Prepend the common prefix and append the common tail to the disk location
    full_disk_location="${common_prefix}${disk_location}${common_tail}"

    # Echo information about the current synchronization
    echo "Syncing URL $url at disk location $full_disk_location, with extra args $extra_args"

    # Call yt-dlp with provided arguments and options
    yt-dlp --all-subs $extra_args --download-archive archive.txt --cookies-from-browser chrome -o "$full_disk_location" "$url"
done <config.tsv
