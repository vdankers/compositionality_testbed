import argparse
import logging
import os
import re
import copy
import json
import random

from typing import List, Tuple

import handlers
from handlers import DatasetHandler
from dataset import Dataset, Sample


def exceptions(handler : DatasetHandler, dataset : Dataset, name : str):
    """For all templates, collect exceptions and save training and testing
    datasets."""

    def collect_exceptions(dataset, template : str, token1 : str, token2 : str) -> Tuple[List[Sample], List[Sample]]:
        """Collect all samples whose source sequence matches the 'template'."""
        exceptions = Dataset()
        regex = re.compile(template)

        new_samples = []
        for sample in dataset:
            match = regex.match(sample.source)
            if not match is None:
                if sample.source.count(token1) == 1 and sample.source.count(token2) == 1:
                    exceptions.add(sample)
                # else:
                #     print(template, sample.source)
            else:
                new_samples.append(sample)

        dataset_exceptions_removed = Dataset(samples=new_samples)
        return exceptions, dataset_exceptions_removed

    def acquire_alternative_targets(exceptions : List[Sample], handler : DatasetHandler, token1 : str, token2 : str) -> List[Sample]:
        """Collect the adapted targets for the exceptions gathered in the source."""
        exceptions_alternative_targets = Dataset()
        samples_to_remove = []
        for sample in exceptions:
            new_target, _, _ = handler.get_target(sample, token1, token2)
            new_target = " ".join(new_target)
            if new_target != sample.target:
                new_sample = Sample(sample.source, new_target)
                exceptions_alternative_targets.add(new_sample)
            else:
                samples_to_remove.append(sample)
        exceptions.remove(samples_to_remove)
        return exceptions_alternative_targets

    n_samples = len(dataset)
    logging.info("Dataset contains {} samples.".format(n_samples))

    for token1 in handler.candidates:
        for token2 in handler.candidates:
            if token1 == token2: continue
            tmp_template = handler.template.format(token1, token2)
            exceptions, dataset_no_exceptions = collect_exceptions(dataset, tmp_template, token1, token2)
            n_exceptions = round(handler.percentage * min(dataset.statistics[token1], dataset.statistics[token2]))

            exceptions.keep_top(n_exceptions)

            logging.info("Template {}, found {} exceptions.".format(
                         tmp_template, len(exceptions)))
            
            exceptions_alternative_targets = acquire_alternative_targets(exceptions, handler, token1, token2)
            # Save training set with exceptions
            dataset_no_exceptions.extend(exceptions_alternative_targets.samples)
            directory = os.path.join(handler.output_dir, "exceptions/train/")
            fname = "train_{}-{}.tsv".format(token1, token2)
            dataset_no_exceptions.save(fname, directory) 

            # Save exceptions adapted target
            fname = "test_adap_{}-{}.tsv".format(token1, token2)
            directory = os.path.join(handler.output_dir, "exceptions/adapted/")
            Dataset(samples=[s for s in exceptions_alternative_targets.samples if handler.count_functions(s.source) == 2]).save(fname, directory)

            # Save exceptions original target
            fname = "test_org_{}-{}.tsv".format(token1, token2)
            directory = os.path.join(handler.output_dir, "exceptions/original/")
            Dataset(samples=[s for s in exceptions.samples if handler.count_functions(s.source) == 2]).save(filename=fname, folder=directory)


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