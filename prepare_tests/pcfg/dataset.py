import os
import random

from collections import Counter


class Dataset:
    def __init__(self, filename : str=None, samples : list=None):
        self.samples = []
        self.statistics = Counter()
        if filename is not None:
            self.load(filename)
        if samples is not None:
            self.samples.extend(samples)
        for s in self.samples:
            self._update_statistics(s)

    def load(self, filename : str):
        """Load a dataset with source and target separated by a tab into a list of
        dictionaries with keys "source" and "target"."""
        with open(filename) as f:
            for line in f:
                line = line.strip()
                # Assume source and target are separated by a tab
                [sequence, target] = line.split("\t")
                self.samples.append(Sample(sequence, target))

    def save(self, filename : str, folder : str=""):
        """Save a dataset with source and target separated by a tab per line."""
        if folder:
            if not os.path.exists(folder):
                os.mkdir(folder)
            filename = os.path.join(folder, filename)

        with open(filename, 'w') as f:
            for sample in self.samples:
                f.write("{}\t{}\n".format(sample.source, sample.target))

    def add(self, sample):
        self.samples.append(sample)
        self._update_statistics(sample)

    def remove(self, samples):
        for sample in samples:
            if sample in self.samples:
                self.samples.remove(sample)
            else:
                for sample2 in self.samples:
                    if sample2.source == sample.source:
                        self.samples.remove(sample2)
                        break
            for token in set(sample.source.split()):
                self.statistics[token] -= 1

    def extend(self, samples):
        self.samples.extend(samples)
        for s in samples:
            self._update_statistics(s)

    def keep_top(self, n):
        self.samples = random.sample(self.samples, min([n, len(self.samples)]))
        self.statistics = Counter()
        for s in self.samples:
            self._update_statistics(s)

    def _update_statistics(self, sample):
        self.statistics.update(set(sample.source.split()))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        return self.samples[i]

    def __str__(self):
        return "\n".join([str(s) for s in self.samples])


class Sample:
    def __init__(self, source, target):
        self.source = source
        self.target = target

    def __str__(self):
        return "Sample, Input: `{}', Target: `{}'".format(self.source, self.target)