import urllib.request, re, sys, os, json




# This was inspired by https://github.com/explanacion/Tatoeba-anki-deckgeneration/blob/main/Tatoeba_anki.py
# Here are some extra features this version supports:
# Scrapes all audios of a language instead of only from tatoeba lists
# Allows multiple translation languages
# Much more customization of translation permissibility
# Scrape is now pausable/stateless, you can safely kill the program and resume later
# Generally minimalized and cleaned up features I found useless
# Overall de-uglified code



# BASIC CONFIGURATION

# Code of the target language (codes are provided below.) https://en.wikipedia.org/wiki/List_of_ISO_639-2_codes
targetlang = "ind"

# Languages you already understand
knownlangs = ["spa", "eng"]

# If a direct translation can't be found, should we use a translation of a translation?
allow_indirect_translations = True



# ADVANCED CONFIGURATION

# Where all the files will be stored. You may want to set this to be your anki media folder.
workspace = "generated_files/" + targetlang

# What character should separate fields in the outputted file? You probably want a tab.
# Do not use a comma, as they appear in the sentences.
separator = '\t'

# How should we prioritize translations?
# If you leave it as 0, it will be automatically generated from your above config values.
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
translation_priority = [[("eng", True), ("eng", False)], [("spa", True), ("spa", False)]]




# A list of languages with audio on tatoeba:
# eng = english
# spa = spanish
# kab = kabyle
# deu = german
# por = portuguese
# fra = french
# hun = hungarian
# rus = russian
# ber = tamazight
# fin = finnish
# epo = esperanto
# wuu = shanghainese
# nld = dutch
# mar = marathi
# cmn = mandarin chinese
# jpn = japanese
# heb = hebrew
# lat = latin
# toki = toki pona
# pol = polish
# dtp = central Dusun
# ces = czech
# ukr = ukrainian
# kor = korean
# tha = thai
# cat = catalan
# cbk = chavacano
# ron = romanian
# tur = turkish
# nst = naga (tangshang)
# frr = north frisian
# shy = tacawit
# nus = nuer
# yue = cantonese






# You probably shouldn't need to touch anything below

















csv_path = workspace+"/import.csv"



def main():
    setupFilesystem()
    generate_translation_priority()
    print("Using translation priority " + str(translation_priority))

    global pagescount, already_in_file

    # Keep track of the number of pages in this list.
    # As soon as we read a page, we will update this to the true value
    pagescount = 999999

    # Let's scan the csv file to see if we already have sentences from a prior run which we can now skip
    already_in_file = open(csv_path).read()

    page_number = 1
    while page_number < pagescount:
        scrapeOnePage(page_number)
        page_number+=1



def scrapeOnePage(page_number):
    html = getHtml('https://tatoeba.org/en/audio/index/' + targetlang + "?page=" + str(page_number))

    # how many pages there are in this list? We don't know until we see at least one page.
    updatePagesCount(html)

    # A list of links to sentences on this page
    links = {}

    split_html = html.split("data-sentence-id=\"")
    skippedFiles = 0
    for splitstring in split_html[1:]:

        # The number according to this segment of html
        num = int(re.search('\d+', splitstring).group(0))

        # Note this sentence as "to-be-downloaded" if we don't already have it.
        if "\t" + str(num) + "\n" not in already_in_file:
            links[num] = num
        else:
            skippedFiles+=1

    print("PAGE " + str(page_number) + "/" + str(pagescount) + ": Skipping " + str(skippedFiles//3) + " sentences already present in the file.")

    # Now go through and actually process all the sentences
    for i in links:
        addSentence(str(i))



# process the link, open it and grab all we need
def addSentence(numstr):
    html = getHtml('https://tatoeba.org/eng/sentences/show/' + numstr)
    json_sentence = re.findall('<div ng-cloak flex.+?sentence-and-translations.+?ng-init="vm.init\(\[\]\,(.+?}), \[\{',procstring(html), re.DOTALL)
    (sentence, translations) = select_translation(json_sentence)

    if translations == []:
        print("  " + numstr + ": No known-language translations found! Skipping...")
        return
    
    # Successfully found translation
    audiourl = 'https://audio.tatoeba.org/sentences/' + targetlang + '/' + numstr + '.mp3'
    audiopath = "generated_files/" + targetlang + "/" + numstr + ".mp3"
    successtext = numstr + ": " + sentence

    if os.path.exists(audiopath):
        print("- " + successtext)
    else:
        urllib.request.urlretrieve(audiourl, audiopath)
        print("a " + successtext)

    appendToFile(numstr, sentence, translations)



# Prioritizes the translation we use.
def select_translation(json_sentence):
    sentence = ''
    translations = []
    for translation_priority_sublist in translation_priority:
        (sentence, translation) = select_translation_from_sublist(json_sentence, translation_priority_sublist)
        translations.append(translation)
    print(" ", end="")
    return (sentence, translations)



def select_translation_from_sublist(json_sentence, translation_priority_sublist):
    sentence = ''
    i = 0
    print("[", end="")
    for (known, direct) in translation_priority_sublist:
        print(known[0], end='')
        i+=1
        json_data = json.loads(json_sentence[0])
        sentence = json_data['text']
        for translations in json_data['translations']:
            for translation in translations:
                direct_translation = 'isDirect' in translation and translation['isDirect']
                if isinstance(translation['lang'], str) and translation['lang'] == known and (direct == direct_translation):
                    print("-"*(len(translation_priority_sublist)-i) + "]", end="")
                    return (sentence, translation['text'])
    print("-"*(len(translation_priority_sublist)-i) + "]", end="")
    return (sentence, '')






















# Helper Functions

def generate_translation_priority():
    global translation_priority
    if translation_priority == 0:
        one_sublist = []
        for known in knownlangs:
            for permissible_indirect in ([True, False] if allow_indirect_translations else [True]):
                one_sublist.append((known, permissible_indirect))
        translation_priority = [one_sublist]

def setupFilesystem():
    if not os.path.exists(workspace):
        try:
            os.mkdir(workspace)
        except:
            print("The script couldn't create a temporary workdir called " + workspace)
            sys.exit(1)
    if not os.path.exists(csv_path):
        csv = open(csv_path, "w")
        csv.close()

def procstring(string):
    res = string
    res=res.replace("&#039;","'")
    res=res.replace("&quot;",'"')
    return res

def updatePagesCount(html):
    global pagescount
    if pagescount != 999999:
        return # We have already computed the real page count
    pagescount = re.findall('page=(\d+?)\D', html)
    if pagescount != []:
        pagescount = 1+max([int(x) for x in pagescount])
    else:
        pagescount = 1 # there is no pagination

def getHtml(url):
    resp = urllib.request.urlopen(url)
    if resp.getcode() != 200:
        print("Error response for search")
        sys.exit(1)
    html = resp.read().decode('utf-8')
    resp.close()
    return html

def appendToFile(num, sentence, translation_list):
    csv = open(csv_path, "a")

    line = '[sound:' + num + ".mp3]" + separator + sentence + separator;
    for t in translation_list:
        line += t + separator
    line += num + "\n"

    csv.write(line)
    csv.close()














if __name__ == "__main__":
    main()
