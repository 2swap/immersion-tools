#!/bin/bash

mkdir -p audio

for ext in mkv webm mp4; do
    for filename in ./*.$ext; do
        # Check if the file exists
        [ -e "$filename" ] || continue

        # Extract the audio codec of the file
        codec=$(ffprobe -loglevel error -select_streams a:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 "$filename")

        base=$(basename "$filename" .$ext)

        case $codec in
            aac)
                output_ext=aac
                ;;
            opus)
                output_ext=opus
                ;;
            mp3)
                output_ext=mp3
                ;;
            vorbis)
                output_ext=ogg
                ;;
            flac)
                output_ext=flac
                ;;
            *)
                # Default to .aac if unknown codec or adjust as per your requirement
                output_ext=aac
                ;;
        esac

        ffmpeg -i "$filename" -c:a copy "audio/$base.$output_ext"
    done
done

