#!/usr/bin/python3

import os
import random
import subprocess
import argparse

WATCHED_FILE = "watched_videos.txt"
BOOKMARK_FILE = "bookmark.txt"
VIDEO_EXTENSIONS = ['.m4v', '.mp4', '.mkv', '.avi', '.webm']
AUDIO_EXTENSIONS = ['.wav', '.ogg', '.mp3', '.flac', '.aac', '.m4a', '.opus']
EXTENSIONS = []

TO_WATCH_LIST = []
WATCHED_IN_BOOKMARK_LIST = []
WATCHED_OUTSIDE_BOOKMARK_LIST = []

DIRECTORIES = []

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

def load_directories_from_bookmark():
    """Loading directories from the bookmark and their subdirectories..."""
    global DIRECTORIES
    assert os.path.exists(BOOKMARK_FILE), f"The bookmark file '{BOOKMARK_FILE}' does not exist."

    DIRECTORIES = []
    
    with open(BOOKMARK_FILE, 'r') as f:
        base_directories = [line.strip() for line in f.readlines() if not line.startswith('#')]

    for directory in base_directories:
        full_directory_path = os.path.join(ROOT_DIR, directory)
        if os.path.isdir(full_directory_path):
            for root, dirs, _ in os.walk(full_directory_path):
                DIRECTORIES.append(root)
    
    assert DIRECTORIES, "No directories were loaded."

def load_videos(search_term, rewatch):
    """Load the watched and unwatched videos lists."""

    global TO_WATCH_LIST, WATCHED_IN_BOOKMARK_LIST, WATCHED_OUTSIDE_BOOKMARK_LIST
    bookmark_videos = load_videos_from_bookmark(search_term)
    if os.path.exists(WATCHED_FILE) and not rewatch:
        with open(WATCHED_FILE, 'r') as f:
            for line in f:
                video = line.strip()
                if video in bookmark_videos:
                    WATCHED_IN_BOOKMARK_LIST.append(video)
                    bookmark_videos.remove(video)
                else:
                    WATCHED_OUTSIDE_BOOKMARK_LIST.append(video)

    TO_WATCH_LIST.extend(bookmark_videos)


def load_videos_from_directory(directory, search_term):
    """Load videos from a specific directory, without including subdirectories,
    and return paths relative to ROOT_DIR."""

    full_directory_path = os.path.join(ROOT_DIR, directory)

    # Assert that the directory exists
    assert os.path.exists(full_directory_path), f"The directory '{full_directory_path}' does not exist."

    videos = []
    for file in os.listdir(full_directory_path):
        full_path = os.path.join(full_directory_path, file)
        if os.path.isfile(full_path) and any(file.lower().endswith(ext.lower()) for ext in EXTENSIONS):
            if not search_term or search_term in full_path:
                # Append the relative path by removing ROOT_DIR prefix
                relative_path = os.path.relpath(full_path, ROOT_DIR)
                videos.append(relative_path)
    return sorted(videos)


def load_videos_from_bookmark(search_term):
    """Load the videos from the bookmark."""

    assert(len(DIRECTORIES)>0)
    all_videos = []

    for directory in DIRECTORIES:
        videos_from_dir = load_videos_from_directory(directory, search_term)
        all_videos.extend(videos_from_dir)

    return all_videos


def play_video(video_path):
    print(video_path)
    print()
    if args.ffplay:
        result = subprocess.run(
            ['ffplay', ROOT_DIR + video_path],
        )
    else:
        cmd = ['vlc', os.path.join(ROOT_DIR, video_path), 'vlc://quit']
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT
        )
    return result.returncode


def mark_as_watched(video_path):
    """Mark video as watched in both the file and the lists."""
    with open(WATCHED_FILE, 'a') as f:
        f.write(video_path + '\n')
    WATCHED_IN_BOOKMARK_LIST.append(video_path)
    TO_WATCH_LIST.remove(video_path)


def print_stats(search_term):
    print()
    max_length = max(len(directory.split('/')[-1]) for directory in DIRECTORIES)

    completely_watched_dirs = []

    for directory in DIRECTORIES:
        dir_name = directory.rstrip('/').split('/')[-1]
        dir_videos = set(load_videos_from_directory(directory, search_term))
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

    print()


def search_videos_from_list(search_term):
    while True:
        os.system('clear')
        if args.shuffle:
            random.shuffle(TO_WATCH_LIST)
        video = TO_WATCH_LIST[0]

        print_stats(search_term)
        play_video(video)

        if args.listen:
            mark_as_watched(video)
            continue  # Proceed to the next video

        while True:
            choice = input("Choose an option:\n"
                           "y: Mark this video as watched and continue (Default)\n"
                           "e: Mark as watched and exit\n"
                           "n: Do not mark as watched and exit\n"
                           "r: Rewatch this video\n"
                           "d: Delete the video and continue\n"
                           "Enter your choice (Y/e/n/r/d): ").lower().strip()

            if choice in ['y', '']:
                mark_as_watched(video)
                break
            elif choice == 'e':
                mark_as_watched(video)
                exit(0)
            elif choice == 'n':
                exit(0)
            elif choice == 'r':
                play_video(video)
            elif choice == 'd':
                confirmation = input(f"Are you sure you want to delete '{video}'? This action cannot be undone. (y/N): ").lower().strip()
                if confirmation == 'y':
                    mark_as_watched(video)
                    os.remove(os.path.join(ROOT_DIR, video))
                    break
                else:
                    print("Deletion canceled.")
            else:
                print("Invalid response.")


def check_working_directory():

    # Check and create WATCHED_FILE if it doesn't exist
    if not os.path.exists(WATCHED_FILE):
        with open(WATCHED_FILE, 'w') as f:
            pass  # This creates an empty file

    # Check and create BOOKMARK_FILE if it doesn't exist
    if not os.path.exists(BOOKMARK_FILE):
        user_input = input(f"The file '{BOOKMARK_FILE}' does not exist. Do you want to create it with empty content? (y/N): ")

        if user_input.lower() != 'y':
            print("Exiting without creating the file.")
            exit()

        with open(BOOKMARK_FILE, 'w') as f:
            # This creates an empty file
            pass


def main(search_term, rewatch):
    global EXTENSIONS
    EXTENSIONS = AUDIO_EXTENSIONS if args.listen else VIDEO_EXTENSIONS
    check_working_directory()

    load_directories_from_bookmark()
    load_videos(search_term, rewatch)

    if(args.stats):
        print_stats(search_term)
        exit()

    search_videos_from_list(search_term)


if __name__ == '__main__':
    # Setup argument parser
    parser = argparse.ArgumentParser(description="Play videos from a folder.")
    parser.add_argument("-s", "--shuffle", help="shuffle videos", action="store_true")
    parser.add_argument("-x", "--stats"  , help="show lists of watched videos", action="store_true")
    parser.add_argument("-r", "--rewatch", help="Include videos which have already been seen", action="store_true")
    parser.add_argument("-n", "--search" , help="start with this directory", type=str)
    parser.add_argument("-l", "--listen" , help="Audio files instead of video files", action="store_true")
    parser.add_argument("-f", "--ffplay" , help="Use ffplay instead of vlc", action="store_true")
    args = parser.parse_args()

    main(args.search, args.rewatch)
