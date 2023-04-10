# Print an empty line
echo

# Check if there is at least one argument provided
if [ "$#" -lt 1 ]; then
    # If not, print usage message and exit
    echo "Usage: subs2srs your/video/file.mkv"
    exit
fi

# Print the audio and subtitle streams of the video file
ffprobe "$1" 2>&1 | grep Stream | grep Audio
ffprobe "$1" 2>&1 | grep Stream | grep Subtitle

# Print an empty line
echo

# Check if there are exactly four arguments provided
if [ "$#" -ne 4 ]; then
    # If not, print usage message and exit
    echo "Usage: subs2srs your/video/file.mkv audio_stream_number subtitle_stream_number media_prefix"
    echo
    exit
fi

# Determine the audio file extension based on the audio stream number of the video file
aud_ext=$(ffprobe "$1" 2>&1 | grep Stream | grep 0:$2 | sed -rn 's/.*Audio: ([a-z]*).*/\1/p')

# Set the subtitle file name and the name of the import file for Anki
subs=anki/subs.ass
import=anki/import_to_anki.tsv

# Remove existing subtitle, import, and audio files and directories
rm -f $subs
rm -f $import
rm -rf anki/audio

# Create the audio directory for Anki
mkdir -p anki/audio

# Extract the subtitle stream from the video file and save it to the subtitle file
ffmpeg -loglevel error -i "$1" -map 0:$3 $subs

# Initialize a counter variable
i=-1

# Read each line of the subtitle file and process it
while read -r line; do
    # Print the line
    echo "$line"
    # Increment the counter
    ((i++))

    # If the line is not a dialogue line, skip to the next line
    if [[ ! $line =~ ^Dialogue.* ]]; then
        continue
    fi

    # Extract the start time, end time, and text from the dialogue line
    start_time=$(echo "$line" | cut -d ',' -f 2)
    end_time=$(echo "$line" | cut -d ',' -f 3)
    text=$(echo "$line" | cut -d ',' -f 10-)

    # Set the name of the audio file for this subtitle
    audio_file_name="$4$i.$aud_ext"

    # Extract the audio from the video file for the duration of the subtitle and save it to the audio file
    ffmpeg -nostdin -i "$1" -ss "${start_time}0" -to "${end_time}0" -q:a 0 -map a "anki/audio/$audio_file_name" > /dev/null 2>&1

    # Add the audio file name and the subtitle text to the import file for Anki
    echo -e "[sound:$audio_file_name]\t$text" >> "$import"
done < "$subs"


