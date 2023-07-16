#!/bin/bash

# Path to the file listing watched videos
WATCHED_FILE="watched_videos.txt"

# Path to the file containing the current video series path
BOOKMARK_FILE="bookmark.txt"

# Function to play the video with VLC
play_video() {
    echo $1
    vlc "$1" vlc://quit
}

# Function to mark a video as watched
mark_as_watched() {
    echo "$1" >> "$WATCHED_FILE"
}

# Function to check if a video has been watched
is_watched() {
    grep -Fxq "$1" "$WATCHED_FILE"
}

# Function to prompt for video completion
ask_completion() {
    read -p "Enter to mark complete the video" choice
}

# Function to search for unwatched videos recursively
search_videos() {
    local path="$1"
    local videos=$(find "$path" -type f \( -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.avi" -o -iname "*.webm" \))

    IFS=$'\n'  # Set the input field separator to only newline character
    for video in $videos; do
        if ! is_watched "$video"; then
            play_video "$video"
            ask_completion && mark_as_watched "$video"
            return
        fi
    done
}

# Entry point
if [[ ! -f "$BOOKMARK_FILE" ]]; then
    echo "Please create a file called '$BOOKMARK_FILE' and provide the path to the current video series."
    exit 1
fi

# Read the path from the video series file
path=$(<"$BOOKMARK_FILE")

while true; do
    search_videos "/media/swap/primary/$path" || exit
done
