import re

def renumber_sentences(input_file, output_file):
    sentence_count = 0  # Start counting sentences

    with open(input_file, "r", encoding="utf-8") as infile, open(output_file, "w", encoding="utf-8") as outfile:
        for line in infile:
            # Detect sentence ID but do NOT modify it
            if line.startswith("# sent_id = "):
                sentence_count += 1  # Increment sentence count

            # Match and update sentence number in "# :: sntXX" line
            elif line.startswith("# :: snt"):
                line = f"# :: snt{sentence_count}\n"

            # Update variables within the sentence-level graph and alignment
            else:
                line = re.sub(r"\bs(\d+)", f"s{sentence_count}", line)  # Only replace full-word sXX variables

            outfile.write(line)

lang = "it"  # Change this to "en", "cs", etc.
input_filename = f"../gold_total_{lang}_test.txt"
output_filename = f"../new_gold_total_{lang}_test.txt"

renumber_sentences(input_filename, output_filename)
