import os

input_file = "watched_videos.txt"
output_file = "watched_videos_filtered.txt"

valid_files = []

# Read and filter existing files
with open(input_file, "r", encoding="utf-8") as infile:
    for line in infile:
        filename = line.strip()
        if not filename:
            continue  # skip empty lines
        full_path = os.path.join("../..", filename)
        if os.path.exists(full_path):
            valid_files.append(filename)

# Sort the list lexicographically
valid_files.sort()

# Write sorted, valid filenames to new file
with open(output_file, "w", encoding="utf-8") as outfile:
    for filename in valid_files:
        outfile.write(filename + "\n")

print(f"Wrote {len(valid_files)} valid, sorted entries to {output_file}")

