import re

def renumber_sentences(input_file, output_file):
    sentence_count = 0

    with open(input_file, "r", encoding="utf-8") as infile, open(output_file, "w", encoding="utf-8") as outfile:
        for line in infile:
            # Match and update sentence ID
            match = re.match(r"# sent_id = ([nw]\d{8})", line)
            if match:
                sentence_count += 1
                line = line

            # Match and update sentence number in "# :: sntXX" line
            elif line.startswith("# :: snt"):
                line = f"# :: snt{sentence_count}\n"

            # Update variables within the sentence-level graph and alignment
            else:
                line = re.sub(r"(?<!\w)s(\d+)", f"s{sentence_count}", line)

            outfile.write(line)

lang = "it"  # en, cs

input_filename = f"../temp_gold_total_{lang}_test.txt"
output_filename = f"../gold_total_{lang}_test.txt"
renumber_sentences(input_filename, output_filename)
