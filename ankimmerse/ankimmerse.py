import os
import subprocess
import shutil
import json
import re
import readline

def make_project_folder():
    project_name = input("Select a project name. This will be appended to all of the generated media files to group them: ")
    media_prefix = project_name
    output_folder_path = os.path.join(os.getcwd(), media_prefix)
    if os.path.exists(output_folder_path):
        print("Seems this project already exists! Continuing where we left off...")
    else:
        os.makedirs(output_folder_path)
    media_directory = os.path.join(output_folder_path, "media")
    if not os.path.exists(media_directory):
        os.makedirs(media_directory)
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

def get_video(output_folder_path):
    video_path_file = os.path.join(output_folder_path, "video_path.txt")
    if os.path.exists(video_path_file):
        print("Subtitle file already exists. Skipping step.")
        print("Video path file already exists. Reading video path from file.")
        with open(video_path_file, 'r') as file:
            video_path = file.readline().strip()
            if os.path.exists(video_path):
                print("Using video path from the file:", video_path)
                return video_path
    video_path = request_path_check_valid("Enter the video file path: ")
    with open(video_path_file, 'w') as file:
        file.write(video_path)
    return video_path

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

def convert_to_srt_time(seconds):
    ms = int((seconds % 1) * 1000)
    seconds = int(seconds)
    minutes = seconds // 60
    seconds %= 60
    hours = minutes // 60
    minutes %= 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"

def generate_srt_with_sound_references(subs_file, stream_index, video_file, media_prefix, output_folder_path):
    ffprobe_output = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", stream_index, "-show_entries", "packet=pts_time,duration_time", "-of", "csv=p=0", video_file], stderr=subprocess.PIPE, text=True)

    timestamps = ffprobe_output.strip().split('\n')
    timestamps = [line.split(",") for line in timestamps]

    audio_files = [f"{media_prefix}_{i+1}_translation.mp3" for i in range(len(timestamps))]

    print_audio_streams(video_file)
    audio_stream = input("Since you chose a bitmap based subtitle, please enter the audio stream index number for a language you understand: ") #TODO check the number is valid

    with open(subs_file, 'w') as subs:
        for i, (begin_time, duration) in enumerate(timestamps):
            begin_time_float = float(begin_time)
            end_time_float = begin_time_float + float(duration)
            begin_time_srt = convert_to_srt_time(begin_time_float)
            end_time_srt = convert_to_srt_time(end_time_float)
            audio_path = os.path.join(output_folder_path, "media", audio_files[i])
            subs.write(f"{i + 1}\n{begin_time_srt} --> {end_time_srt}\n{audio_files[i]}\n\n")
            if not os.path.exists(audio_path):
                cmd = ["ffmpeg", "-nostdin", "-i", video_file, "-map", f"0:{audio_stream}", "-ss", begin_time_srt.replace(",", "."), "-to", end_time_srt.replace(",", "."), audio_path]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

def get_subtitles(video_file, output_folder_path, media_prefix):
    subs = os.path.join(output_folder_path, "subs.srt")
    if os.path.exists(subs):
        print("Subtitle file already exists. Skipping step.")
        return

    try:
        ffprobe_subtitles_output = subprocess.check_output(["ffprobe", video_file, "-select_streams", "s", "-show_streams", "-of", "json"], stderr=subprocess.PIPE, text=True)
        subtitles_data = json.loads(ffprobe_subtitles_output)
        print("\n\n\nSubtitle Streams:")

        for stream in subtitles_data.get("streams", []):
            index = stream.get("index")
            codec_name = stream.get("codec_name")
            language = stream["tags"].get("language")
            warning = " -> This subtitle appears to be bitmap-based. A translation audio stream will be required. Choose a different stream if possible." if codec_name == "dvd_subtitle" else ""
            print(f"Index: {index}, Codec Name: {codec_name}, Language: {language} {warning}")
    except subprocess.CalledProcessError as e:
        print("Error occurred while running ffprobe for subtitle streams:")
        print(e.stderr)
        return

    use_subs_file = None
    while use_subs_file == None:
        subs_type_char = input("Type S if you would like to use an internal subtitle stream (i.e. if you see an appropriate stream above) or F if you would like to use an external subtitle file: ").lower()
        if subs_type_char == 'f':
            use_subs_file = True
        elif subs_type_char == 's':
            use_subs_file = False
        else:
            print("Option not recognized! Try again.")

    if use_subs_file:
        subs_in = request_path_check_valid("\nUsing external subs file. Enter the subtitle file path: ")
        # Copy the provided subtitle file to the subs file for Anki
        subprocess.run(["ffmpeg", "-i", subs_in, subs], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    else:
        chosen_sub = None
        while chosen_sub == None:
            subs_stream = input("\nUsing internal subtitle stream. Enter the subtitle stream index number: ") #TODO check the number is valid
            for stream in subtitles_data.get("streams", []):
                index = stream.get("index")
                codec_name = stream.get("codec_name")
                if str(subs_stream) == str(index):
                    chosen_sub = stream
                    break
            if chosen_sub == None:
                print("Index not recognized. Try again!")

        if chosen_sub.get("codec_name") == "dvd_subtitle":
            print("Generating SRT file with sound references for bitmap subtitles...")
            generate_srt_with_sound_references(subs, subs_stream, video_file, media_prefix, output_folder_path)
        else:
            print("Extracting and converting subtitles from video. This should not take more than 2 minutes.")
            # Extract the subtitle stream from the video file and save it to the subtitle file in SRT format
            subprocess.run(["ffmpeg", "-i", video_file, "-map", f"0:{subs_stream}", subs], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    print("Removing HTML and other inline markup including <> and {} blocks from subtitles...")
    clean_subs(subs)

    # Prompt user
    user_response = input(f"\nYou have the option to remove extraneous subtitles by editing the subtitle file.\nDo you want to open it with vim for editing? (Y/n): ")

    if user_response.lower() != 'n':
        try:
            subprocess.run(['vim', subs], check=True)
            input("Press enter when done editing.")
        except (subprocess.CalledProcessError, FileNotFoundError):
            input(f"Failed to open {subs} with vim. Please edit the file manually and press enter to continue.")
    else:
        print("Proceeding with unedited subtitles.")

def print_audio_streams(video_file):
    ffprobe_audio_output = subprocess.check_output(["ffprobe", video_file, "-select_streams", "a", "-show_streams", "-of", "json"], stderr=subprocess.PIPE, text=True)
    audio_data = json.loads(ffprobe_audio_output)
    print("\n\n\nAudio Streams:")

    for stream in audio_data.get("streams", []):
        index = stream.get("index")
        codec_name = stream.get("codec_name")
        language = stream["tags"].get("language")
        print(f"Index: {index}, Codec Name: {codec_name}, Language: {language}")

def get_audio(video_file, output_folder_path):
    audio_file = os.path.join(output_folder_path, "audio.mp3")
    if os.path.exists(audio_file):
        print("Audio file already exists. Skipping step.")
        return

    try:
        print_audio_streams(video_file)
        audio_stream = input("Enter the audio stream index number: ") #TODO check the number is valid
        print("Extracting and converting audio from video. This will take a few minutes.")

        # Extract the audio stream using ffmpeg and save it to the audio file
        subprocess.run(["ffmpeg", "-i", video_file, "-map", f"0:{audio_stream}", audio_file], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    except subprocess.CalledProcessError as e:
        print("Error occurred while running ffprobe/ffmpeg for audio extraction:")
        print(e.stderr)

def parse_subtitle_entry(subs_file, buffer):

    try:
        entry_lines = []

        # Get the initial file position
        initial_pos = subs_file.tell()

        # Read the lines until an empty line is encountered, indicating the end of the entry
        while True:
            line = subs_file.readline().strip()

            # Empty line indicates the end of the entry
            if not line:
                # Check if the current position is the same as the initial position
                # If it is, then we have reached the end of the file
                current_pos = subs_file.tell()
                if current_pos == initial_pos:
                    return "EOF"  # End of file, no more entries
                break  # Empty line within the entry, end of the entry

            entry_lines.append(line)

        # Check if the entry has at least three lines (index, timestamps, and dialogue)
        if len(entry_lines) >= 3:
            # Parse the index
            index = entry_lines[0]

            # Parse the timestamps (begin_time and end_time)
            begin_time_str, end_time_str = re.findall(r'\d+:\d+:\d+,\d+', entry_lines[1])
            begin_time_str = begin_time_str.replace(",", ":")
            end_time_str = end_time_str.replace(",", ":")

            # Convert the timestamps to seconds
            begin_time_seconds = sum(x * int(t) for x, t in zip([3600, 60, 1, 1/1000], begin_time_str.split(":")[0:4]))
            end_time_seconds = sum(x * int(t) for x, t in zip([3600, 60, 1, 1/1000], end_time_str.split(":")[0:4]))

            begin_time_seconds -= buffer
            end_time_seconds += buffer

            # Convert the adjusted times back to their original format
            begin_time_adjusted = '{:02d}:{:02d}:{:02d}.{}'.format(int(begin_time_seconds // 3600), int((begin_time_seconds % 3600) // 60), int(begin_time_seconds % 60), int((begin_time_seconds % 1) * 1000))
            end_time_adjusted = '{:02d}:{:02d}:{:02d}.{}'.format(int(end_time_seconds // 3600), int((end_time_seconds % 3600) // 60), int(end_time_seconds % 60), int((end_time_seconds % 1) * 1000))

            # Concatenate the dialogue lines into a single string
            dialogue = ' '.join(entry_lines[2:]).replace("\"", "")

            return (index, begin_time_adjusted, end_time_adjusted, dialogue)
        else:
            print(entry_lines)
            return "skip"
    except Exception as e:
        raise ValueError(f"Error occurred while parsing SRT entry: {str(e)}")

def make_deck(video_file, output_folder_path, media_prefix):
    print("\nCreating cards!")

    # Read the subtitles and cut up the video
    import_path = os.path.join(output_folder_path, "import.tsv")
    subs_path = os.path.join(output_folder_path, "subs.srt")
    full_audio_path = os.path.join(output_folder_path, "audio.mp3")


    while True:
        buffer_input = input("Enter a value for buffer (default is 0.5): ")

        try:
            if not buffer_input:
                buffer = 0.5
            else:
                buffer = float(buffer_input)
            print("Buffer:", buffer)
            break  # Exit the loop if input and conversion are successful

        except ValueError:
            print("Error: Please enter a valid numeric value for buffer.")

    with open(subs_path, "r") as subs_file, open(import_path, "w") as import_file_handle:
        while True:
            srt_data = parse_subtitle_entry(subs_file, buffer)
            if srt_data == "EOF":
                print("Done!\n")
                return
            if srt_data == "skip":
                continue
            index, begin_time, end_time, dialogue = srt_data
            print(f"{index} {dialogue}")

            media_directory = os.path.join(output_folder_path, "media")
            audio_name = f"{media_prefix}_{index}.mp3"
            audio_path = os.path.join(media_directory, audio_name)

            # Generate audio snippet
            if not os.path.exists(audio_path):
                subprocess.run(["ffmpeg", "-nostdin", "-i", full_audio_path, "-acodec", "copy", "-ss", begin_time, "-to", end_time, audio_path], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

            # Bound image size to 1280x720
            image_scale_filter = "scale='min(1280,iw)':'min(720,ih)'"
            image_begin_name = f"{media_prefix}_{index}-begin.jpg"
            image_begin_path = os.path.join(media_directory, image_begin_name)
            image_end_name = f"{media_prefix}_{index}-end.jpg"
            image_end_path = os.path.join(media_directory, image_end_name)

            # Generate images
            if not os.path.exists(image_begin_path):
                subprocess.run(["ffmpeg", "-nostdin", "-ss", begin_time, "-i", video_file, "-vf", image_scale_filter, "-vframes", "1", "-q:v", "2", image_begin_path], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            if not os.path.exists(image_end_path):
                subprocess.run(["ffmpeg", "-nostdin", "-ss", end_time, "-i", video_file, "-vf", image_scale_filter, "-vframes", "1", "-q:v", "2", image_end_path], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

            # Write the line as an Anki card
            import_file_handle.write(f"{audio_name}\t{dialogue}\t<img src='{image_begin_name}'>\t<img src='{image_end_name}'>\n")

def move_files_to_anki_media(output_folder_path):
    answer = input("Do you want to copy all files from anki/data/ to ~/anki_media/? (y/n): ").lower()
    if answer == "y":
        media_directory = os.path.join(output_folder_path, "media")
        destination_dir = os.path.expanduser("~/anki_media/")
        print("Copying files...")
        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)
        for file_name in os.listdir(media_directory):
            source_file_path = os.path.join(media_directory, file_name)
            destination_file_path = os.path.join(destination_dir, file_name)
            shutil.copy(source_file_path, destination_file_path)
        print("Done!")
    else:
        print("Skipping file copy.")

def main():
    # enable tab completion
    readline.parse_and_bind("tab: complete")

    output_folder_path, media_prefix = make_project_folder()

    video_file = get_video(output_folder_path)
    get_subtitles(video_file, output_folder_path, media_prefix)
    get_audio(video_file, output_folder_path)

    make_deck(video_file, output_folder_path, media_prefix)

    move_files_to_anki_media(output_folder_path)


if __name__ == "__main__":
    main()
