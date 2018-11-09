import argparse
import os
import codecs
import logging


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--source', type=str, required=True)
    parser.add_argument('-t', '--target', type=str, required=True)
    parser.add_argument('-i', '--input', type=str, required=True)
    args = vars(parser.parse_args())


    if not os.path.isfile(args["input"]):
        logging.error("Please enter an existing input file.")
    else:
        with codecs.open(args["source"], 'w', "utf-8") as f_s, \
             codecs.open(args["target"], 'w', "utf-8") as f_t, \
             codecs.open(args["input"], 'r', "utf-8") as f_i:
            for line in f_i:
                [source, target] = line.split("\t")
                source = source.strip()
                target = target.strip()
                f_s.write("{}\n".format(source))
                f_t.write("{}\n".format(target))