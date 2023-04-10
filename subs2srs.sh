#!/bin/bash

# Check if the -f flag is provided and set the subtitle format accordingly
if [[ "$1" == "-f" ]]; then
    use_subs_file=true
    subtitle_format="vtt"
    subs_in="$2"
    video_file="$3"
    audio_stream="$4"
    media_prefix="$5"
else
    use_subs_file=false
    subtitle_format="ass"
    video_file="$1"
    audio_stream="$2"
    subs_stream="$3"
    media_prefix="$4"
fi

echo "subs_in: $subs_in"
echo "subs_stream: $subs_stream"
echo "video: $video_file"
echo "audio: $audio_stream"
echo "media prefix: $media_prefix"

# Check if the required arguments are provided
if [[ "$#" -lt 1 ]]; then
    # If not, print the audio and subtitle streams of the video file and exit
    ffprobe "$1" 2>&1 | grep Stream | grep Audio
    ffprobe "$1" 2>&1 | grep Stream | grep Subtitle
    echo "Usage: subs2srs [-f vtt] your/video/file.mkv"
    exit
fi

# Set the subtitle file name and the name of the import file for Anki
subs=anki/subs
import=anki/import_to_anki.tsv

# Cleanup old files
rm -r anki/
mkdir -p anki/audio

# Determine the audio file extension based on the audio stream number of the video file
aud_ext=$(ffprobe "$video_file" 2>&1 | grep Stream | grep "0:$audio_stream" | sed -rn 's/.*Audio: ([a-z]*).*/\1/p')
echo "detected audio format $aud_ext"

if [[ "$use_subs_file" == true ]]; then
    # If the -f flag is provided, make sure the required arguments are provided as well
    if [[ "$#" -ne 5 ]]; then
        echo "-f flag usage: subs2srs -f vtt/subs/file video/file.mkv audio_stream_number media_prefix"
        echo
        exit
    fi
    subs=anki/subs.vtt
    # Copy the provided subtitle file to the subs file for Anki
    cp "$subs_in" "$subs"
else
    # If the -f flag is not provided, make sure the required arguments are provided
    if [[ "$#" -ne 4 ]]; then
        echo "Usage: subs2srs video/file.mkv audio_stream_number subtitle_stream_number media_prefix"
        echo
        exit
    fi
    subs=anki/subs.ass

    # Extract the subtitle stream from the video file and save it to the subtitle file
    ffmpeg -loglevel error -i "$video_file" -map 0:$subs_stream $subs
fi

i=-1

while read -r line; do
    ((i++))

    # Parse the subtitle line based on the subtitle format
    if [[ $subtitle_format == "ass" ]]; then
        if [[ ! $line =~ ^Dialogue.* ]]; then
            continue
        fi
        start_time=$(echo "$line" | cut -d ',' -f 2)
        end_time=$(echo "$line" | cut -d ',' -f 3)
        text=$(echo "$line" | cut -d ',' -f 10-)
    elif [[ $subtitle_format == "vtt" ]]; then
        if [[ $line != *"-->"* ]]; then
            continue
        fi
        start_time=$(echo "$line" | awk -F ' --> ' '{print $1}')
        end_time=$(echo "$line" | awk -F ' --> ' '{print $2}')
        read -r text
    fi

    # Create the audio file name based on the media prefix and index
    audio_file_name="$media_prefix$i.$aud_ext"
    
    echo "$start_time $end_time $text $audio_file_name"

    # Generate audio snippet
    if [[ $subtitle_format == "ass" ]]; then
        ffmpeg -nostdin -i "$video_file" -ss "${start_time}0" -to "${end_time}0" -q:a 0 -map a "anki/audio/$audio_file_name" > /dev/null 2>&1
    elif [[ $subtitle_format == "vtt" ]]; then
        ffmpeg -nostdin -i "$video_file" -ss "$start_time" -to "$end_time" -q:a 0 -map a "anki/audio/$audio_file_name" > /dev/null #2>&1
    fi

    # Write the line as an Anki card
    echo -e "[sound:$audio_file_name]\t$text" >> "$import"

done < "$subs"

