import urllib.request, re, sys, os, json
from urllib.error import URLError, HTTPError
from typing import AnyStr, Optional, List, Tuple, Any



# This was inspired by https://github.com/explanacion/Tatoeba-anki-deckgeneration/blob/main/Tatoeba_anki.py
# Here are some extra features this version supports:
# Scrapes all audios of a language instead of only from tatoeba lists
# Allows multiple translation languages
# Much more customization of translation permissibility
# Scrape is now pausable/stateless, you can safely kill the program and resume later
# Generally minimalized and cleaned up features I found useless
# Overall de-uglified code




# ADVANCED CONFIGURATION

# What character should separate fields in the outputted file? You probably want a tab.
# Do not use a comma, as they appear in the sentences.
separator = '\t'

# How should we prioritize translations?
# 
# This is a list of lists of tuples.
# Each sub-list will have a translation chosen from its first available tuple.
# Each tuple element contains a language code and a boolean representing whether the translation is direct.
# 
# As an example:
# translation_priority = [[("eng", True), ("spa", True), ("eng", False), ("spa", False)]]
# This will prioritize english direct translations
#                 then spanish direct translations
#                 then english indirect translations
#                 then spanish indirect translations
#                 If none of the above are found, we skip the sentence.
# 
# translation_priority = [[("eng", True), ("eng", False)], [("spa", True), ("spa", False)]]
# This will download one english translation and one spanish translation, prioritizing direct translations,
# assuming they exist.
translation_priority = [[("spa", True ),
                         ("spa", False)],
                        [("ind", True ),
                         ("ind", False)],
                        [("eng", True ),
                         ("eng", False)]]




# A list of languages with audio on tatoeba:
# eng = english
# spa = spanish
# kab = kabyle
# deu = german
# por = portuguese
# fra = french
# nld = dutch
# rus = russian
# hun = hungarian
# jpn = japanese
# pol = polish
# ber = tamazight
# fin = finnish
# epo = esperanto
# wuu = shanghainese
# mar = marathi
# yue = cantonese
# ind = indonesian
# cmn = mandarin chinese
# ita = italian
# heb = hebrew
# lat = latin
# toki = toki pona
# tha = thai
# ara = arabic
# dtp = central Dusun
# tur = turkish
# ces = czech
# ukr = ukrainian
# mfa = Melayu Kelantan-Pattani
# swe = Swedish
# cat = catalan
# cbk = chavacano
# ron = romanian
# nst = naga (tangshan)
# sat = Santali
# frr = north frisian
# nus = nuer
# shy = tacawit
# arz = Egyptian Arabic






# You probably shouldn't need to touch anything below




















def main():
    """
    The main function that orchestrates the entire sentence scraping and processing workflow.
    """

    # Set up the file system to ensure all necessary directories and files are in place
    setup_filesystem(workspace, tsv_path)

    # Generate the translation priority list
    print(f"Using translation priority {translation_priority}")

    # Initialize the page count to a high number which will be updated with the actual count
    pages_count = 999999

    # Read the TSV file to find which sentences have already been processed
    with open(tsv_path, 'r') as file:
        already_in_file = file.read()

    # Begin scraping from the first page
    page_number = 1
    while page_number < pages_count:
        # Scrape a single page and process its sentences
        scrape_one_page(page_number, already_in_file, pages_count, workspace)
        
        # Update the page number for the next iteration
        page_number += 1

        # Optionally, you can save the last processed page number to a file or database
        # to resume later from where you left off


def scrape_one_page(page_number, already_in_file, pages_count, workspace):
    """
    Scrapes a single page of sentences from Tatoeba for a specified language.

    :param page_number: The current page number to scrape.
    :param already_in_file: A set containing sentence numbers already processed.
    :param pages_count: The total number of pages available for scraping.
    :param workspace: The directory where audio files are stored.
    """
    # Fetch the HTML content of the page
    html = get_html(f'https://tatoeba.org/en/audio/index/{target_lang}?page={page_number}')

    # Update the total number of pages if not already known
    update_pages_count(html)

    # Initialize a dictionary to hold sentence links
    links_to_process = {}

    # Split the HTML content by the data attribute for sentence ID
    split_html = html.split("data-sentence-id=\"")
    skipped_files_count = 0

    # Process each HTML segment to extract sentence numbers
    for split_string in split_html[1:]:
        # Extract the sentence number
        sentence_number_match = re.search(r'\d+', split_string)
        if sentence_number_match:
            sentence_number = int(sentence_number_match.group(0))

            # Check if we already have this sentence, if not add to links_to_process
            if f"\t{sentence_number}\n" not in already_in_file:
                links_to_process[sentence_number] = sentence_number
            else:
                skipped_files_count += 1

    # Log the number of skipped files (sentences)
    print(f"PAGE {page_number}/{pages_count}: Skipping {skipped_files_count//3} sentences already present in the file.")

    # Process each sentence
    for sentence_id in links_to_process:
        add_sentence(str(sentence_id))




# Function to process the provided HTML content and extract usable text
def process_html_string(html: str) -> str:
    """
    Replaces HTML entities with their corresponding characters.

    :param html: The HTML content as a string.
    :return: The processed string with HTML entities replaced.
    """
    processed_html = html.replace("&#039;", "'").replace("&quot;", '"')
    return processed_html

# Function to extract JSON data for a sentence from the HTML page
def extract_json_sentence(html: str) -> str:
    """
    Extracts the JSON containing sentence and translations from the HTML content using a regular expression.

    :param html: The HTML content as a string.
    :return: The JSON string extracted from the HTML.
    """
    pattern = '<div ng-cloak flex.+?sentence-and-translations.+?ng-init="vm.init\(\[\]\,(.+?}), \[\{'
    json_data_match = re.findall(pattern, process_html_string(html), re.DOTALL)
    return json_data_match[0] if json_data_match else ''

# Function to add a sentence and its translations to a file
def add_sentence(num_str: str) -> None:
    """
    Retrieves a sentence and its translations from Tatoeba, downloads the audio, and appends the data to a file.

    :param num_str: The sentence number as a string.
    """
    try:
        # Get the HTML content from Tatoeba
        html = get_html('https://tatoeba.org/eng/sentences/show/' + num_str)
        json_sentence = extract_json_sentence(html)

        # If no JSON data is found, skip the sentence
        if not json_sentence:
            print(f"  {num_str}: No JSON data found! Skipping...")
            return

        # Select the best translation based on the priority
        sentence, translations = select_translation(json_sentence, translation_priority)

        # If no translations are found, skip the sentence
        if not translations:
            print(f"  {num_str}: No known-language translations found! Skipping...")
            return
        
        # Handle audio download and storage
        audiourl = f'https://audio.tatoeba.org/sentences/{target_lang}/{num_str}.mp3'
        audiopath = os.path.join(workspace, f"{num_str}.mp3")
        success_text = f"{num_str}: {sentence}"

        if os.path.exists(audiopath):
            print(f"- {success_text}")
        else:
            urllib.request.urlretrieve(audiourl, audiopath)
            print(f"a {success_text}")

        # Append the data to the file
        append_to_file(num_str, sentence, translations, tsv_path)
    except Exception as e:
        print(f"An error occurred while processing sentence {num_str}: {e}")




def select_translation(json_sentence: str, translation_priority: List[List[Tuple[str, bool]]]) -> Tuple[str, List[str]]:
    """
    Selects the best translation based on a priority list.

    :param json_sentence: A JSON string containing the sentence and its translations.
    :param translation_priority: A nested list of tuples indicating language and direct translation priority.
    :return: A tuple containing the original sentence and a list of selected translations.
    """
    original_sentence = ''
    selected_translations = []
    
    # Parse the JSON data once, as it does not change in the loop.
    json_data = json.loads(json_sentence)
    original_sentence = json_data['text']
    
    # Iterate over each priority sublist and select the translation.
    for priority_sublist in translation_priority:
        translation = select_translation_from_sublist(json_data, priority_sublist)
        selected_translations.append(translation)

    return original_sentence, selected_translations

def select_translation_from_sublist(json_data: Any, translation_priority_sublist: List[Tuple[str, bool]]) -> str:
    """
    Selects a translation from a given sublist of translation priorities.

    :param json_data: The parsed JSON data containing the sentence and translations.
    :param translation_priority_sublist: A list of tuples with language and if direct translation is required.
    :return: The selected translation text.
    """
    for language, requires_direct in translation_priority_sublist:
        for translations in json_data['translations']:
            for translation in translations:
                is_direct_translation = translation.get('isDirect', False)
                if translation['lang'] == language and requires_direct == is_direct_translation:
                    return translation['text']

    return ''  # Return an empty string if no translation matched the priority list.






















# Helper Functions

def setup_filesystem(workspace: str, tsv_path: str) -> None:
    """
    Sets up the necessary filesystem for operation by ensuring that the workspace and TSV paths exist.

    :param workspace: The directory path for the workspace.
    :param tsv_path: The file path for the TSV.
    """

    # Example usage:
    # setup_filesystem('/path/to/workspace', '/path/to/tsv_file.tsv')

    try:
        os.makedirs(workspace, exist_ok=True)
    except Exception as e:
        print(f"The script couldn't create a temporary workdir called {workspace}. Error: {e}")
        sys.exit(1)

    # Ensure the TSV file exists
    if not os.path.exists(tsv_path):
        with open(tsv_path, "w") as tsv_file:
            # The file is created and closed immediately as it's opened in write mode.
            pass


def process_string(original_string: str) -> str:
    """
    Processes an HTML-encoded string by converting specific HTML entities to their respective characters.

    :param original_string: The string containing HTML entities.
    :return: A new string with HTML entities replaced by their respective characters.
    """
    result_string = original_string
    result_string = result_string.replace("&#039;", "'")
    result_string = result_string.replace("&quot;", '"')
    return result_string

def update_pages_count(html: str, current_pages_count: Optional[int] = 999999) -> int:
    """
    Updates the number of pages by finding all occurrences of 'page=x' in the HTML, where x is a number.

    :param html: The HTML content as a string.
    :param current_pages_count: The current pages count, if already known. Defaults to 999999.
    :return: The updated pages count.
    """

    # Example usage:
    # html_content = "<html>...pagination...page=3...</html>"
    # pages_count = update_pages_count(html_content)
    # print(pages_count)

    # If we already have the real pages count, return it.
    if current_pages_count != 999999:
        return current_pages_count
    
    # Find all 'page=x' occurrences and extract the number 'x'.
    found_pages = re.findall(r'page=(\d+?)\D', html)
    
    # If we found any page numbers, calculate the max and add 1.
    if found_pages:
        # Convert all found page numbers to integers and find the max.
        max_page = 1 + max(map(int, found_pages))
        return max_page
    else:
        # Default to 1 if no pagination is found.
        return 1



def get_html(url: AnyStr) -> AnyStr:
    """
    Fetches the HTML content from a given URL.

    :param url: The URL from which to fetch the HTML content.
    :return: A string containing the decoded HTML content.
    :raises HTTPError: An error from the server if the response code is not 200.
    :raises URLError: A failure to reach the server.
    """

    # Example usage:
    # print(get_html("http://example.com"))

    try:
        with urllib.request.urlopen(url) as response:
            if response.getcode() != 200:
                raise HTTPError(url, response.getcode(), "Error response for search", response.headers, None)
            html_content = response.read().decode('utf-8')
            return html_content
    except HTTPError as e:
        print(f'HTTP error occurred: {e.code} - {e.reason}')
        raise
    except URLError as e:
        print(f'Failed to reach the server: {e.reason}')
        raise




def append_to_file(num: str, sentence: str, translation_list: list, tsv_path: str) -> None:
    """
    Appends a line to a TSV file with a specific format.

    :param num: The identifier number, which is also used for the mp3 filename.
    :param sentence: The sentence to be recorded in the file.
    :param translation_list: A list of translations to be appended after the sentence.
    :param tsv_path: The path to the TSV file.
    """

    # Example usage
    # append_to_file('001', 'Hello, world!', ['Hola, mundo!', 'Bonjour, monde!'], 'translations.tsv')

    # Constructing the line to write to the TSV file
    line_elements = [f'[sound:{num}.mp3]'] + [sentence] + translation_list + [num]
    line = separator.join(line_elements) + "\n"

    # Writing the constructed line to the TSV file
    with open(tsv_path, "a") as tsv_file:
        tsv_file.write(line)











def setup():
    global target_lang, workspace, tsv_path
    target_lang = sys.argv[1]
    workspace = os.path.join("generated_files", target_lang)
    tsv_path = os.path.join(workspace, "import.tsv")


if __name__ == "__main__":
    # Check if at least one command line argument is provided
    print(sys.argv)
    if len(sys.argv) > 1:
        setup()
        main()
    else:
        print("No language code provided.")
