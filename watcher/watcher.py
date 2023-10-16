import os
import random
import subprocess
import argparse

WATCHED_FILE = "watched_videos.txt"
BOOKMARK_FILE = "bookmark.txt"
VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.webm']

TO_WATCH_LIST = []
WATCHED_IN_BOOKMARK_LIST = []
WATCHED_OUTSIDE_BOOKMARK_LIST = []
DIRECTORIES = []


def load_directories_from_bookmark():
    """Loading directories from the bookmark..."""

    global DIRECTORIES
    assert os.path.exists(BOOKMARK_FILE), f"The bookmark file '{BOOKMARK_FILE}' does not exist."
    
    with open(BOOKMARK_FILE, 'r') as f:
        # Ignore lines starting with # and strip whitespace
        DIRECTORIES = [line.strip() for line in f.readlines() if not line.startswith('#')]


def load_videos():
    """Load the watched and unwatched videos lists."""

    global TO_WATCH_LIST, WATCHED_IN_BOOKMARK_LIST, WATCHED_OUTSIDE_BOOKMARK_LIST
    bookmark_videos = load_videos_from_bookmark()
    if os.path.exists(WATCHED_FILE):
        with open(WATCHED_FILE, 'r') as f:
            for line in f:
                video = line.strip()
                if video in bookmark_videos:
                    WATCHED_IN_BOOKMARK_LIST.append(video)
                    bookmark_videos.remove(video)
                else:
                    WATCHED_OUTSIDE_BOOKMARK_LIST.append(video)

    TO_WATCH_LIST.extend(bookmark_videos)


def load_videos_from_directory(directory):
    """Load videos from a specific directory."""
    
    full_directory_path = os.path.join("/media/swap/primary", directory)
    
    # Assert that the directory exists
    assert os.path.exists(full_directory_path), f"The directory '{full_directory_path}' does not exist."

    videos = []
    for root, _, files in os.walk(full_directory_path):
        # Sort files alphanumerically
        sorted_files = sorted(files)
        for file in sorted_files:
            if any(file.endswith(ext) for ext in VIDEO_EXTENSIONS):
                videos.append(os.path.join(root, file))
    return videos


def load_videos_from_bookmark():
    """Load the videos from the bookmark."""

    assert(len(DIRECTORIES)>0)
    all_videos = []

    for directory in DIRECTORIES:
        videos_from_dir = load_videos_from_directory(directory)
        all_videos.extend(videos_from_dir)

    return all_videos


def play_video(video_path):
    print(video_path)
    print()
    subprocess.run(['vlc', video_path, 'vlc://quit'], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def mark_as_watched(video_path):
    """Mark video as watched in both the file and the lists."""
    with open(WATCHED_FILE, 'a') as f:
        f.write(video_path + '\n')
    WATCHED_IN_BOOKMARK_LIST.append(video_path)
    TO_WATCH_LIST.remove(video_path)


def print_stats():
    print()
    max_length = max(len(directory.split('/')[-1]) for directory in DIRECTORIES)

    completely_watched_dirs = []

    for directory in DIRECTORIES:
        dir_name = directory.split('/')[-1]
        dir_videos = set(load_videos_from_directory(directory))
        watched_in_dir = len([video for video in WATCHED_IN_BOOKMARK_LIST if video in dir_videos])
        total_in_dir = len(dir_videos)

        # If directory is completely watched, add it to the list
        if watched_in_dir == total_in_dir:
            completely_watched_dirs.append(dir_name)
            continue

        # Create the visual representation
        completed = '#' * watched_in_dir
        not_completed = '.' * (total_in_dir - watched_in_dir)

        visual_representation = completed + not_completed

        # Print the results
        for i in range(0, len(visual_representation), 50):
            chunk = visual_representation[i:i+50]
            if i == 0:
                print(f"{dir_name.ljust(max_length)} | {chunk}")
            else:
                print(f"{''.ljust(max_length)} | {chunk}")

    # Print the list of completely watched directories
    if completely_watched_dirs:
        print("\nDirectories completely watched:")
        for dir_name in completely_watched_dirs:
            print(f"- {dir_name}")

    print()



def search_videos_from_list(shuffle):
    for video in TO_WATCH_LIST.copy():
        os.system('clear')
        print_stats()
        play_video(video)
        input("Enter to mark complete the video")
        mark_as_watched(video)

def check_working_directory():

    # Check and create WATCHED_FILE if it doesn't exist
    if not os.path.exists(WATCHED_FILE):
        with open(WATCHED_FILE, 'w') as f:
            pass  # This creates an empty file

    # Check and create BOOKMARK_FILE if it doesn't exist
    if not os.path.exists(BOOKMARK_FILE):
        print(f"Please provide the paths to the video directories in the '{BOOKMARK_FILE}' file.")
        with open(BOOKMARK_FILE, 'w') as f:  # This creates an empty file
            pass
        exit()


def main(shuffle=False):
    check_working_directory()

    load_videos()

    if(args.stats):
        print_stats()
        exit()

    if shuffle:
        random.shuffle(TO_WATCH_LIST)
    search_videos_from_list(shuffle)


if __name__ == '__main__':
    # Setup argument parser
    parser = argparse.ArgumentParser(description="Play videos from a folder.")
    parser.add_argument("-s", "--shuffle", help="shuffle videos"              , action="store_true")
    parser.add_argument("-x", "--stats"  , help="show lists of watched videos", action="store_true")
    args = parser.parse_args()

    load_directories_from_bookmark()
    main(shuffle=args.shuffle)
