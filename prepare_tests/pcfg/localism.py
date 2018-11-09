import argparse
import logging
import os
import re
import copy
import json
import random

import handlers
from dataset import Dataset, Sample


def localism(handler : handlers.DatasetHandler, dataset : Dataset, name : str):
    """Construct unrolled datasets for localism experiments."""

    # Create new dataset containing the unrolled samples
    unrolled_dataset = Dataset()
    n = round(handler.percentage * len(dataset))

    for sample in dataset[:n]:
        # Primitive samples cannot be unrolled, as unrolled = original
        if handler.is_primitive(sample.source): continue

        # The unroll function must be specified per dataset handler
        unrolled_samples = handler.unroll(sample)

        # Add `unrolled' or `original' to the samples to indicate the type
        # for the evaluation script
        for (source, target) in unrolled_samples[:-1]:
            unrolled_dataset.add(Sample("unrolled\t{}".format(source), target))
        unrolled_dataset.extend([
            Sample("unrolled\t{}".format(unrolled_samples[-1][0]), sample.target),
            Sample("original\t{}".format(sample.source), sample.target)
        ])

    # Save new dataset
    directory = os.path.join(handler.output_dir, "localism")
    filename = "unrolled_{}.tsv".format(name)
    unrolled_dataset.save(filename=filename, folder=directory)
    logging.info("Prepared unrolled dataset, saved as {}.".format(filename))


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, default="config.json")
    parser.add_argument('--log_level', type=str, default="info")
    args = vars(parser.parse_args())
    logging.basicConfig(level=args["log_level"].upper(),
                        format='%(asctime)s - %(levelname)s - %(message)s')

    with open(args["config"]) as f: config = json.load(f)

    if not os.path.isfile(config["general"]["train"]):
        logging.error("Please enter an existing file for the training dataset.")
    elif not os.path.isfile(config["general"]["test"]):
        logging.error("Please enter an existing file for the testing dataset.")
    else:
        print("Parameters\n----------")
        for k, v in config["localism"].items():
            print("{} : {}".format(k, v))
        print()

        handler = getattr(handlers, config["general"]["handler"])
        handler = handler(config=config, mode="localism")
        localism(handler, handler.train, "train")
        localism(handler, handler.test, "test")