echo

if [ "$#" -lt 1 ]; then
    echo "Usage: subs2srs your/video/file.mkv"
    exit
fi

ffprobe "$1" 2>&1 | grep Stream | grep Audio
ffprobe "$1" 2>&1 | grep Stream | grep Subtitle

echo

if [ "$#" -ne 4 ]; then
    echo "Usage: subs2srs your/video/file.mkv audio_stream_number subtitle_stream_number media_prefix"
    echo
    exit
fi

aud_ext=$(ffprobe "$1" 2>&1 | grep Stream | grep 0:$2 | sed -rn 's/.*Audio: ([a-z]*).*/\1/p')
subs=anki/subs.ass
import=anki/import_to_anki.tsv

rm -f $subs
rm -f $import
rm -rf anki/audio

mkdir -p anki/audio

ffmpeg -loglevel error -i "$1" -map 0:$3 $subs

i=-1

while read -r line; do
    echo "$line"
    ((i++))

    if [[ ! $line =~ ^Dialogue.* ]]; then
        continue
    fi

    start_time=$(echo "$line" | cut -d ',' -f 2)
    end_time=$(echo "$line" | cut -d ',' -f 3)
    text=$(echo "$line" | cut -d ',' -f 10)
    audio_file_name="$4$i.$aud_ext"

    ffmpeg -nostdin -i "$1" -ss "${start_time}0" -to "${end_time}0" -q:a 0 -map a "anki/audio/$audio_file_name" > /dev/null 2>&1

    echo -e "[sound:$audio_file_name]\t$text" >> "$import"
done < "$subs"

