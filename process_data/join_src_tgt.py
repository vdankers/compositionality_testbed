import argparse
import os
import codecs
import logging


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--source', type=str, required=True)
    parser.add_argument('-t', '--target', type=str, required=True)
    parser.add_argument('-o', '--output', type=str, required=True)
    args = vars(parser.parse_args())


    if not os.path.isfile(args["source"]):
        logging.error("Please enter an existing source file.")
    elif not os.path.isfile(args["target"]):
        logging.error("Please enter an existing target file.")
    else:
        with codecs.open(args["source"], 'r', "utf-8") as f_s, \
             codecs.open(args["target"], 'r', "utf-8") as f_t, \
             codecs.open(args["output"], 'w', "utf-8") as f_o:
            for source, target in zip(f_s, f_t):
                source = source.strip()
                target = target.strip()
                f_o.write("{}\t{}\n".format(source, target))
