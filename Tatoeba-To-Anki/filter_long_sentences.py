import os, sys

def filter_tsv(input_file, output_file, max_length):
    with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
        for line in infile:
            fields = line.split('\t')
            sentence = fields[1]

            if len(sentence) <= max_length:
                outfile.write(line)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: script.py lang_code max_length")
    else:
        input_file = os.path.join("generated_files", sys.argv[1], "import.tsv")
        output_file = os.path.join("generated_files", sys.argv[1], "short_sentences_only.tsv")
        max_length = int(sys.argv[2])  # Convert the command line argument to an integer

        filter_tsv(input_file, output_file, max_length)

