import argparse
import logging
import os
import re
import copy
import json
import random

from typing import List, Tuple

import handlers
from dataset import Dataset, Sample


def exceptions(handler : handlers.DatasetHandler, dataset : Dataset, name : str):
    """For all templates, collect exceptions and save training and testing
    datasets."""

    def collect_exceptions(dataset, template : str) -> Tuple[List[Sample], List[Sample]]:
        """Collect all samples whose source sequence matches the 'template'."""
        exceptions = Dataset()
        regex = re.compile(template)

        for sample in dataset:
            match = regex.match(sample.source)
            if not match is None: exceptions.add(sample)

        dataset_exceptions_removed = copy.deepcopy(dataset)
        for sample in exceptions: dataset_exceptions_removed.remove(sample)
        return exceptions, dataset_exceptions_removed

    def acquire_alternative_targets(exceptions : List[Sample]) -> List[Sample]:
        """Collect the adapted targets for the exceptions gathered in the source."""
        exceptions_alternative_targets = Dataset()
        for sample in exceptions:
            new_target = self.get_target(sample)
            new_sample = Sample(sample.source, new_target)
            exceptions_alternative_targets.add(new_sample)
        return exceptions_alternative_targets

    n_samples = len(dataset)
    logging.info("Dataset contains {} samples.".format(n_samples))

    for token1 in handler.candidates:
        for token2 in handler.candidates:
            tmp_template = handler.template.format(token1, token2)
            exceptions, dataset_no_exceptions = collect_exceptions(dataset, tmp_template)
            n_exceptions = round(handler.percentage * min(dataset.statistics[token1], dataset.statistics[token2]))
            exceptions.keep_top(n_exceptions)

            logging.info("Template {}, found {} exceptions.".format(
                         tmp_template, len(exceptions)))

            fname = "test_org_{}-{}.tsv".format(token1, token2)
            directory = os.path.join(handler.output_dir, "exceptions")
            exceptions.save(filename=fname, folder=directory)
            # exceptions_alternative_targets = acquire_alternative_targets(exceptions)
            # fname = "test_adap_exception-{}_composition-{}_replacement-{}.tsv".format(
            #             exception, composition, replacement
            #         )
            # exceptions_alternative_targets.save(fname, handler.output_dir)


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
    else:
        print("Parameters\n----------")
        for k, v in config["exceptions"].items():
            print("{} : {}".format(k, v))
        print()

        handler = getattr(handlers, config["general"]["handler"])
        handler = handler(config=config, mode="exceptions")
        exceptions(handler, handler.train, "train")