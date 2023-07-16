#include <iostream>
#include <fstream>
#include <map>
#include <bits/stdc++.h>
#include <set>
#include <vector>
#include <algorithm>
#include <cctype>
#include <cstring>
#include <string>
using namespace std;

typedef map<string,int> wordmap;
set<int> punctuation;

bool is_not_punctuation(char c){
    return punctuation.find(c) != punctuation.end();
}

bool hasEnding (std::string const &fullString, std::string const &ending) {
    if (fullString.length() >= ending.length()) {
        return (0 == fullString.compare (fullString.length() - ending.length(), ending.length(), ending));
    } else {
        return false;
    }
}

void to_lower(string &str){
    for(int i = 0; str[i]; i++){
        str[i] = tolower(str[i]);
    }
    int aaa = str.find("ى", 0);
    if(aaa != -1){
        str = str.substr(0, aaa) + "ي" + str.substr(aaa + 2, str.length());
    }
}

vector<pair<string,int>> vectorize(wordmap map, bool strategy, int bound){
    vector<pair<string,int>> vec( map.begin(), map.end() );

    sort( vec.begin(), vec.end(), 
           []( const auto & lhs, const auto & rhs ) 
           { return lhs.second > rhs.second; } );
    vec = vector<pair<string, int>>(vec.begin(), vec.begin()+bound);
    if(strategy){
        sort( vec.begin(), vec.end(), 
               []( const auto & lhs, const auto & rhs ) 
               { return lhs.first > rhs.first; } );
    }
    return vec;
}

wordmap postprocess(wordmap map){
    wordmap copy;

    wordmap::iterator it;

    for (it = map.begin(); it != map.end(); it++) {
        bool added = false;
        string str = it->first;
        if (hasEnding(str, "ة") || hasEnding(str, "ه")) {
            string cut = str.substr(0, str.length()-2);
            if (map.count(cut+"ة") && map.count(cut+"ه")) {
                added = true;
                copy[cut+"ه"+" / "+cut+"ة"] = map[cut+"ه"]+map[cut+"ة"];
            }
        }
        if (!added)
            copy[str] = it->second;
    }

    return copy;
}

void print_list(vector<pair<string,int>> vec, ofstream out){
    for (int i = 0; i < vec.size(); i++){
        auto item = vec[i];
        out << item.first << " --- " << item.second << endl;
    }
    out.close();
}

void remove_punctuation(string &text){
    text.erase(remove_if(text.begin(), text.end(), ptr_fun(&is_not_punctuation)), text.end());
    if(text.rfind("ال", 0) == 0){
        text = text.substr(4);
    }
    if(hasEnding(text, "ين")){
        text = text.substr(0, text.length()-4);
    }
}

wordmap get_frequency(string path){
    ifstream file;
    file.open(path);
    wordmap frequency_map;
    string word = "";
    while (file >> word) {
        remove_punctuation(word);
        to_lower(word);
        if(word == "")
            continue;
        if (frequency_map.find(word) == frequency_map.end())
            frequency_map[word] = 1;
        else
            frequency_map[word]++;
    }
    file.close();
    return frequency_map;
}

wordmap fuse(wordmap map1, wordmap map2){
    wordmap map_result( map1 );

    for (auto it=map2.begin(); it!=map2.end(); ++it) {
        if ( map_result[it->first] )
            map_result[it->first] += it->second;
        else
            map_result[it->first] = it->second;
    }
    return map_result;
}

wordmap read_wordmap_file(string filename){
    ifstream file(filename);
    wordmap map;
    string word = "";
    int i = 1;
    while (file >> word) {
        map[word] = 100000000/i;
        i++;
    }
    return map;
}

wordmap read_wordmap_file_with_numbers(string filename){
    ifstream file(filename);
    wordmap map;
    int count = 0;
    int i = 1;
    for (string line; getline(file, line); ) {

        //tokenize line
        vector <string> tokens;
        stringstream check1(line);
        string intermediate;
        while(getline(check1, intermediate, '\t')) tokens.push_back(intermediate);
        cout << tokens[0] << tokens[1] << endl;

        map[tokens[0]] = stoi(tokens[1]);
        i++;
    }
    return map;
}

void make_arabic(){
    string punct_string = "...,(){}[]-'\";:<>/\\|!@#–-$%^&*_+=`~0123456789“”…?";
    for (int i = 0; i < punct_string.length(); i++) {
        punctuation.insert(punct_string[i]);
    }
    wordmap map = get_frequency("../../Arabic/wikipedia.txt");
    map = postprocess(map);
    vector<pair<string, int>> vec = vectorize(map, false, 2000);
    print_list(vec, ofstream("arabic [4k].txt"));
}

void make_arabic_2(){
    string punct_string = "...,(){}[]-'\";:<>/\\|!@#–-$%^&*_+=`~0123456789“”…?";
    for (int i = 0; i < punct_string.length(); i++) {
        punctuation.insert(punct_string[i]);
    }
    wordmap map = get_frequency("Egyptian Tweets.tsv");
    map = postprocess(map);
    vector<pair<string, int>> vec = vectorize(map, false, 2000);
    print_list(vec, ofstream("arabic [4k].txt"));
}

int make_hindi()
{
    wordmap wordlist1 = read_wordmap_file("../../Indian Langs/HI1K/Wordlist.txt");
    wordmap wordlist2 = read_wordmap_file("../../Indian Langs/HI1K/Wordlist2.txt");
    wordmap final_list = fuse(wordlist1, wordlist2);
    cout << "fused" << final_list.size() << endl;
    vector<pair<string, int>> vec = vectorize(final_list, false, 2000);
    print_list(vec, ofstream("../../Indian Langs/HI1K/hindilist.txt"));
    return 0;
}

int make_viet()
{
    wordmap wordlist1 = read_wordmap_file_with_numbers("viet.txt");
    wordmap wordlist2 = read_wordmap_file_with_numbers("viet2.txt");
    wordmap final_list = fuse(wordlist1, wordlist2);
    cout << "fused" << final_list.size() << endl;
    vector<pair<string, int>> vec = vectorize(final_list, false, 5000);
    print_list(vec, ofstream("vietfused.txt"));
    return 0;
}

int main()
{
    make_arabic_2();
    return 0;
}

