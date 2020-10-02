from itertools import groupby

def process_file(filename):
    print('processing ' + filename)
    contents = open(filename, 'r') 
    lines = contents.readlines()

    cleaned_lines = []
    for line in lines:
        if not (line and line.strip()) or line.isspace():
            continue

        cleaned_lines.append(line)

    
    result = []
    is_first = True
    for line in cleaned_lines:
        result.append(line)

        if '-->' in line:
            if not is_first:
                result.insert(len(result)-2, '\n')

            if is_first:
                is_first = False

    result.append('\n')

    to_remove = []
    is_first = True
    for i in range(len(result)):
        if '-->' in result[i]:
            if is_first:
                is_first = False
                continue 

            if '-->' in result[i-3]:
                to_remove.append(i-4)
                to_remove.append(i-3)
                to_remove.append(i-2)

    to_remove.reverse()

    for idx in to_remove:
        del result[idx]

    return result


# Converts .srt file into .txt file with cleaned subtitles
def process_srt_file(lines):
    #print('processing ' + filename)
    #contents = open(filename, 'r') 
    #lines = contents.readlines()

    block = []
    result = []
    for line in lines:
        stripped_line = line.strip()

        if not (line and line.strip()) or line.isspace():
            # If result is empty we can't do any lookback
            if len(result) > 0:
                # Remove duplicate lines
                last_block = result[len(result)-1]
                if block[2] in last_block:
                    del block[2]

                if len(block) <= 2:
                    block = []
                    continue

            # Collapse multiple lines into one single line
            if len(block) > 2:
                line = block[2]
                for l in block[3:]:
                    line += (' ' + l)

                block[2] = line
            
            result.append(block)
            block = []
            continue
        else:
            block.append(stripped_line)

            if line == lines[-1]:
                last_block = result[len(result)-1] if len(result) > 0 else []
                if block[2] in last_block:
                    del block[2]

                if len(block) <= 2:
                    block = []

                result.append(block)

    return result


# Converts cleaned subtitles into informational blocks
def get_parsed_srt_blocks(lines):
    flatten = lambda l: [item for sublist in l for item in sublist]
    _lines = flatten(lines)

    working_block = {}
    blocks = []
    count = 0
    for line in _lines:
        if count % 3 == 1:
            times = line.split('-->')
            working_block['start_time'] = times[0].strip()
            working_block['end_time'] = times[1].strip()

        if count % 3 == 2:
            working_block['text'] = line.strip()
            working_block['word_count'] = len(working_block['text'].strip().split(' '))
            blocks.append(working_block)
            working_block = {}

        count += 1

    return blocks


# Merges multiple subtitle blocks together while maintaining the correct timestamps
# NOTE: THE BLOCKS MUST BE IN THE CORRECT ORDER WITH RESPECT TO THE TIMINGS!!!
def merge_blocks(blocks):
    text = ''
    for block in blocks:
        text += ' ' + block['text']

    return {
        'start_time': blocks[0]['start_time'],
        'end_time': blocks[-1]['end_time'],
        'text': text.strip(),
        'word_count': len(text.strip().split(' '))
    }


# Merges blocks with fewer than 10 words into a single, larger block while maintaining the correct timestamps
# Also duplicates some text to catch any phrases that cross subtitle boundaries
def convert_blocks_to_final_form(filename):
    blocks = get_parsed_srt_blocks(filename)
    
    result = []

    word_count = 0
    blocks_to_be_merged = []

    stop = len(blocks)
    i = 0
    block_start = 0
    while i < stop:
        block = blocks[i]

        blocks_to_be_merged.append(block)
        word_count += block['word_count']

        if (word_count > 10 and i != block_start) or block == blocks[-1]:
            word_count = 0
            block_start = i
            result.append(merge_blocks(blocks_to_be_merged))
            blocks_to_be_merged = []

            if i < stop-1:
                i -= 1

        i += 1


    while result[-1]['word_count'] < 10:
        result[-2] = merge_blocks([result[-2], result[-1]])
        del result[-1]

    return result


def get_episode_number(filename):
    parts = filename.split(' ')
    idx = parts.index('Episode')
    return parts[idx+1]


def do_all_processing_for_file(filename):
    data = process_file(filename)
    data = process_srt_file(data)

    result = convert_blocks_to_final_form(data)

    for r in result:
        r['episode_number'] = get_episode_number(filename)
        time = r['start_time']
        r['start_time'] = int(time[:2]) * 3600 + int(time[3:5]) * 60 + int(time[6:8])
        del r['end_time']

    return result


from os import listdir
from os.path import isfile, join

def get_all_episodes(path="."):
    result = []

    for f in listdir(path):
        if isfile(join(path, f)):
            if 'Episode' in f:
                result.append(int(get_episode_number(f)))

    result.sort()
    return result

def get_missing_episodes():
    episodes = get_all_episodes()

    missing_episodes = []
    # There were 551 episodes at the time of writing this...
    for i in range(1, 552):
        if i not in episodes:
            missing_episodes.append(i)

    return missing_episodes


mypath = '.'
onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]

all_subs = []
for f in onlyfiles:
    if f.endswith('.srt'):
        all_subs.extend(do_all_processing_for_file(f))



import csv

result_data = [['episode_number', 'transcription', 'start_time']]

for e in all_subs:
    time = e['start_time']
    text = e['text']
    episode_number = e['episode_number']
    result_data.append([episode_number, text, time])

myFile = open('transcription_data.csv', 'w')
with myFile:
    writer = csv.writer(myFile)
    writer.writerows(result_data)

myFile.close()
