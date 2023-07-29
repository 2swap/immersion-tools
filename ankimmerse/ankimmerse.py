import os
import subprocess
import shutil
import time
import json
import re
import readline

def make_project_folder():
    project_name = input("Select a project name. This will be appended to all of the generated media files to group them: ")
    media_prefix = f"ankimmerse_{project_name}"
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_folder_name = f"{media_prefix}_{timestamp}"
    output_folder_path = os.path.join(os.getcwd(), output_folder_name)
    os.makedirs(output_folder_path)
    return output_folder_path, media_prefix

def request_path_check_valid(prompt):
    path = None
    while True:
        path = input(prompt).replace("\\", "").strip()
        if os.path.exists(path):
            return path
        else:
            print("Error: The specified file does not exist.")
    return path

def clean_subs(srt_path):
    with open(srt_path, 'r', encoding='utf-8') as f:
        srt_lines = f.readlines()

    # Regular expression patterns to match HTML tags and comments
    html_pattern = re.compile(r'<.*?>')
    comment_pattern = re.compile(r'{.*?}')

    # Remove HTML tags and comments from each line in the subtitles
    cleaned_lines = []
    for line in srt_lines:
        line = html_pattern.sub('', line)  # Remove HTML tags
        line = comment_pattern.sub('', line)  # Remove comments
        cleaned_lines.append(line)

    # Write the cleaned subtitles back to the SRT file
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.writelines(cleaned_lines)

def get_subtitles(video_file, output_folder_path):
    try:
        ffprobe_subtitles_output = subprocess.check_output(["ffprobe", video_file, "-select_streams", "s", "-show_streams", "-of", "json"], stderr=subprocess.PIPE, text=True)
        subtitles_data = json.loads(ffprobe_subtitles_output)
        print("\n\n\nSubtitle Streams:")

        for stream in subtitles_data.get("streams", []):
            index = stream.get("index")
            codec_name = stream.get("codec_name")
            language = stream["tags"].get("language")
            print(f"Index: {index}, Codec Name: {codec_name}, Language: {language}")
    except subprocess.CalledProcessError as e:
        print("Error occurred while running ffprobe for subtitle streams:")
        print(e.stderr)
        return None

    use_subs_file = None
    while use_subs_file == None:
        subs_type_char = input("Type S if you would like to use an internal subtitle stream (i.e. if you see an appropriate stream above) or F if you would like to use an external subtitle file: ").lower()
        if subs_type_char == 'f':
            use_subs_file = True
        elif subs_type_char == 's':
            use_subs_file = False
        else:
            print("Option not recognized! Try again.")

    subs = os.path.join(output_folder_path, "subs.srt")
    if use_subs_file:
        subs_in = request_path_check_valid("\nUsing external subs file. Enter the subtitle file path: ")
        # Copy the provided subtitle file to the subs file for Anki
        subprocess.run(["ffmpeg", "-i", subs_in, subs], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    else:
        subs_stream = input("\nUsing internal subtitle stream. Enter the subtitle stream index number: ") #TODO check the number is valid
        print("Extracting and converting subtitles from video. This should not take more than 2 minutes.")

        # Extract the subtitle stream from the video file and save it to the subtitle file in SRT format
        subprocess.run(["ffmpeg", "-i", video_file, "-map", f"0:{subs_stream}", subs], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    print("Removing HTML and other inline markup including <> and {} blocks from subtitles...")
    clean_subs(subs)

    input(f"\nPlease remove extraneous subtitles by editing {subs} (optional.) Press enter when done editing, or if you wish to import all subtitles.")

def get_audio(video_file, output_folder_path):
    try:
        ffprobe_audio_output = subprocess.check_output(["ffprobe", video_file, "-select_streams", "a", "-show_streams", "-of", "json"], stderr=subprocess.PIPE, text=True)
        audio_data = json.loads(ffprobe_audio_output)
        print("\n\n\nAudio Streams:")

        for stream in audio_data.get("streams", []):
            index = stream.get("index")
            codec_name = stream.get("codec_name")
            language = stream["tags"].get("language")
            print(f"Index: {index}, Codec Name: {codec_name}, Language: {language}")

        audio_stream = input("Enter the audio stream index number: ") #TODO check the number is valid
        print("Extracting and converting audio from video. This will take a few minutes.")

        # Extract the audio stream using ffmpeg and save it to the audio file
        audio_file = os.path.join(output_folder_path, "audio.mp3")
        subprocess.run(["ffmpeg", "-i", video_file, "-map", f"0:{audio_stream}", audio_file], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    except subprocess.CalledProcessError as e:
        print("Error occurred while running ffprobe/ffmpeg for audio extraction:")
        print(e.stderr)

def parse_subtitle_entry(subs_file):
    try:
        entry_lines = []

        # Read the lines until an empty line is encountered, indicating the end of the entry
        while True:
            line = subs_file.readline().strip()
            if not line:  # Empty line indicates the end of the entry
                if not entry_lines: # EOF
                    return None
                break
            entry_lines.append(line)

        # Check if the entry has at least three lines (index, timestamps, and dialogue)
        if len(entry_lines) >= 3:
            # Parse the index
            index = entry_lines[0]

            # Parse the timestamps (begin_time and end_time)
            begin_time, end_time = re.findall(r'\d+:\d+:\d+,\d+', entry_lines[1])

            # Concatenate the dialogue lines into a single string
            dialogue = ' '.join(entry_lines[2:])

            return (index, begin_time.replace(",", "."), end_time.replace(",", "."), dialogue)
        else:
            print(entry_lines)
            raise ValueError("Invalid SRT entry: Entry does not contain the expected number of lines.")
    except Exception as e:
        raise ValueError(f"Error occurred while parsing SRT entry: {str(e)}")

def make_deck(video_file, output_folder_path, media_prefix):
    print("\nCreating cards!")
    media_directory = os.path.join(output_folder_path, "media")
    os.makedirs(media_directory)

    # Read the subtitles and cut up the video
    import_path = os.path.join(output_folder_path, "import.tsv")
    subs_path = os.path.join(output_folder_path, "subs.srt")
    full_audio_path = os.path.join(output_folder_path, "audio.mp3")
    with open(subs_path, "r") as subs_file, open(import_path, "w") as import_file_handle:
        while True:
            srt_data = parse_subtitle_entry(subs_file)
            if srt_data == None:
                print("Done!\n")
                return
            index, begin_time, end_time, dialogue = srt_data
            print(f"{index} {dialogue}")

            audio_name = f"{media_prefix}_{index}.mp3"
            audio_path = os.path.join(media_directory, audio_name)
            image_begin_name = f"{media_prefix}_{index}-begin.jpg"
            image_begin_path = os.path.join(media_directory, image_begin_name)
            image_end_name = f"{media_prefix}_{index}-end.jpg"
            image_end_path = os.path.join(media_directory, image_end_name)

            # Generate audio snippet
            subprocess.run(["ffmpeg", "-nostdin", "-i", full_audio_path, "-acodec", "copy", "-ss", begin_time, "-to", end_time, audio_path], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

            # Generate images
            subprocess.run(["ffmpeg", "-nostdin", "-ss", begin_time, "-i", video_file, "-vframes", "1", "-q:v", "2", image_begin_path], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            subprocess.run(["ffmpeg", "-nostdin", "-ss", end_time  , "-i", video_file, "-vframes", "1", "-q:v", "2", image_end_path  ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

            # Write the line as an Anki card
            import_file_handle.write(f"[sound:{audio_name}]\t{dialogue}\t<img src='{image_begin_name}'>\t<img src='{image_end_name}'>\n")

def move_files_to_anki_media(output_folder_path):
    answer = input("Do you want to move all files from anki/data/ to ~/anki_media/? (y/n): ").lower()
    if answer == "y":
        media_directory = os.path.join(output_folder_path, "media")
        destination_dir = os.path.expanduser("~/anki_media/")
        print("Moving files...")
        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)
        for file_name in os.listdir(source_dir):
            source_file_path = os.path.join(source_dir, file_name)
            destination_file_path = os.path.join(destination_dir, file_name)
            shutil.move(source_file_path, destination_file_path)
        print("Done!")
    else:
        print("Skipping file copy.")

def main():
    # enable tab completion
    readline.parse_and_bind("tab: complete")

    output_folder_path, media_prefix = make_project_folder()

    video_file = request_path_check_valid("Enter the video file path: ")
    get_subtitles(video_file, output_folder_path)
    get_audio(video_file, output_folder_path)

    make_deck(video_file, output_folder_path, media_prefix)

    move_files_to_anki_media(output_folder_path)


if __name__ == "__main__":
    main()
