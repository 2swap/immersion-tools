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
mkdir -p anki/data

# Determine the audio file extension based on the audio stream number of the video file
aud_ext=$(ffprobe "$video_file" 2>&1 | grep Stream | grep "0:$audio_stream" | sed -rn 's/.*Audio: ([a-z]*).*/\1/p')
echo "detected audio format $aud_ext"

if [[ "$use_subs_file" == true ]]; then
    echo "Using external subs file"
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
    echo "Using internal subtitle stream"
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
echo "Extracted subtitles."
read -p "Press enter to begin deck creation, after removing extraneous subs. (optional)"

audio_tag_number=-1

while read -r line; do
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
        text=""
        nextline=""
        while IFS= read -r nextline && [[ "$(printf '%s' "$nextline" | tr -d '[:space:]')" != "" ]]; do
            nextline=$(echo "$nextline" | tr -d '\r\n')
            text="$text $nextline"
        done
    fi
    
    ((audio_tag_number++))

    # Remove all occurrences of <...something...> or {...something...} from the text variable, and get rid of
    # leading or trailing whitespace.
    text=$(echo "$text" | sed -E 's/<[^>]*>//g; s/\{[^}]*\}//g; s/^[[:space:]]+//; s/[[:space:]]+$//;')
    
    start_time=$(echo "000${start_time}000" | sed -E 's/.*([0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9]).*/\1/')
      end_time=$(echo "000${end_time}000"   | sed -E 's/.*([0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9]).*/\1/')

    # Create the audio file name based on the media prefix and index
    audio_file_name="$media_prefix$audio_tag_number.$aud_ext"
    
    echo "$text"

    # Generate audio snippet
    ffmpeg -nostdin -i "$video_file" -acodec copy -ss "$start_time" -to "$end_time" -map 0:$audio_stream "anki/data/$audio_file_name" > /dev/null 2>&1

    # Generate images
    image_start_file_name="$media_prefix$audio_tag_number-1.jpg"
    ffmpeg -nostdin -ss "$start_time" -i "$video_file" -vframes 1 -q:v 2 "anki/data/$image_start_file_name" > /dev/null 2>&1

    image_end_file_name="$media_prefix$audio_tag_number-2.jpg"
    ffmpeg -nostdin -ss "$end_time" -i "$video_file" -vframes 1 -q:v 2 "anki/data/$image_end_file_name" > /dev/null 2>&1

    # Write the line as an Anki card
    echo -e "[sound:$audio_file_name]\t$text\t<img src='$image_start_file_name'>\t<img src='$image_end_file_name'>" >> "$import"

done < "$subs"


read -p "Do you want to move all files from anki/data/ to ~/anki_media/? (y/n) " answer

if [ "$answer" == "y" ]
then
  echo "Moving files..."
  mv anki/data/* ~/anki_media/
  echo "Done!"
else
  echo "Aborting."
fi
