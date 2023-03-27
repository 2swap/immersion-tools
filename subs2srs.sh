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
while IFS= read -r line; do
    ((i++))
    if [[ ! $line =~ ^Dialogue.* ]]; then
        continue
    fi
    starttime=$(echo $line | sed -rn 's/Dialogue[^,]*,([^,]*),([^,]*),[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,(.*)/\1/p')
    [ -z "$starttime" ] && continue
    endtime=$(echo $line | sed -rn 's/Dialogue[^,]*,([^,]*),([^,]*),[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,(.*)/\2/p')
    text=$(echo $line | sed -rn 's/Dialogue[^,]*,([^,]*),([^,]*),[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,(.*)/\3/p')
    audiofilename="$4$i.$aud_ext"
    ffmpeg -i "$1" -ss "$starttime"0 -to "$endtime"0 -q:a 0 -map a anki/audio/$audiofilename && echo -e "[sound:$audiofilename]\t$text" >> $import && ((i))
done < $subs

