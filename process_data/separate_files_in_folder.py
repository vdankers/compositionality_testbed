import argparse
import os
import codecs
import logging


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', type=str, required=True, help="Input folder.")
    parser.add_argument('-o', '--output', type=str, required=True, help="Output folder.")
    args = vars(parser.parse_args())

    if not os.path.exists(args["input"]):
        logging.error("Please enter an existing input folder.")
    if not os.path.exists(args["output"]):
        os.mkdir(args["output"])
    else:
        for file in os.listdir(args["input"]):
            source_sequences = []
            targets = []

            full_path = os.path.join(args["input"], file)
            if not os.path.isdir(full_path):
                [name, extension] = file.split(".")

                # Check if this is an already separated file
                if "src" in name or "tgt" in name:
                    continue

                with codecs.open(full_path, 'r', 'utf-8') as f:
                    for line in f:
                        [source, target] = line.split("\t")
                        source_sequences.append(source.strip())
                        targets.append(target.strip())

                with codecs.open(os.path.join(args["output"], "{}_{}.{}".format(name, "src", extension)), 'w', 'utf-8') as f:
                    f.write("\n".join(source_sequences))

                with codecs.open(os.path.join(args["output"], "{}_{}.{}".format(name, "tgt", extension)), 'w', 'utf-8') as f:
                    f.write("\n".join(targets))
