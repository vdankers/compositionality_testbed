import re
import os
import random
import logging
import subprocess

from typing import List, Tuple, Dict
from dataset import Dataset, Sample


class DatasetHandler:
    """
    General class written for a specific dataset, specifying how to unroll
    existing source sequences and how to generate new targets for adapted
    source sequences.

    General attributes:
        output_dir: directory to store data needed for compositionality tests.
        train: filename of training dataset.
        test: filename of testing dataset.
        evaluate_command: command to run to get the accuracy for test set.

    Attributes for exception generation:
        template: pattern to match exceptions by.
        position: whether the word that switches meaning is in position one or two.
        percentage: percentage of exceptions to generate.
        replacements: which word to replace with which other word.
        candidates: which words can be used to generate exceptions.

    Attributes for localism experiments:
        percentage: percentage of training sequences to unroll.
    """
    def __init__(self, config : Dict[str, Dict], mode : str):
        self.output_dir = config["general"]["output_dir"]
        self.train = Dataset(filename=config["general"]["train"])
        self.test = Dataset(filename=config["general"]["test"])
        self.evaluate_command = config["general"]["evaluate_command"]
        if mode == "exceptions":
            self.template = config["exceptions"]["template"]
            self.position = config["exceptions"]["position"]
            self.percentage = config["exceptions"]["percentage"]
            self.replacements = config["exceptions"]["replacements"]
            self.candidates = config["exceptions"]["candidates"]
        elif mode == "localism":
            self.percentage = config["localism"]["percentage"]

    def unroll(self, sample : Sample, output : Tuple[str, List[Tuple[str, str]], int], variable_counter : int) -> Tuple[str, List[Tuple[str, str]], int]:
        raise NotImplementedError("To be implemented")
        return sequence, output, variable_counter

    def get_target(self, sample : Sample) -> str:
        raise NotImplementedError("To be implemented")
        return sequence

    def get_test_accuracy(self, experiment_type : str, fname : str) -> float:
        raise NotImplementedError("To be implemented")
        return accuracy


class PCFGHandler(DatasetHandler):
    """
    Dataset handler written for PCFG dataset.
    """
    def __init__(self, config : Dict[str, Dict], mode : str):
        super().__init__(config, mode)
        self.functions = ["echo", "shift", "reverse", "copy", "append", "prepend"]

    def unroll(self, sample : Sample):
        source = self._place_brackets(sample.source)
        _, unrolled_samples, _ = self._unroll_recursively(source, [], 0)
        return unrolled_samples

    def get_target(self, sample : Sample, token1 : str, token2 : str) -> str:
        sequence = self._place_brackets(sample.source)
        sequence = self._get_target_recursively(sequence, token1, token2)
        return sequence

    def is_primitive(self, sequence : str) -> bool:
        function_calls = self.count_functions(sequence)
        return True if function_calls == 1 else False

    def count_functions(self, sequence : str) -> int:
        function_calls = 0
        for token in sequence.split():
            if token in self.functions: function_calls += 1
        return function_calls

    def _unroll_recursively(self, sequence : str, output : Tuple[str, List[Tuple[str, str]], int], variable_counter : int) -> (str, Tuple[str, List[Tuple[str, str]], int], int):
        if sequence.count("(") > 1:
            [function, rest] = sequence.split('(', 1)
            function = function.lstrip().rstrip()
            rest = rest.rsplit(')', 1)[0].lstrip().rstrip()
            if function == "append" or function == "prepend":
                arg1, arg2 = self._get_args(rest)
                target1, output, variable_counter = self._unroll_recursively(arg1, output, variable_counter)
                target2, output, variable_counter = self._unroll_recursively(arg2, output, variable_counter)
                target3 = "_{}".format(variable_counter + 1)
                output.append(("{} {} , {}".format(function, target1, target2), target3))
                return target3, output, variable_counter + 1                  
            else:
                target1, output, variable_counter = self._unroll_recursively(rest, output, variable_counter)
                target2 = "_{}".format(variable_counter + 1)
                output.append(("{} {}".format(function, target1), target2))
                return target2, output, variable_counter + 1
        elif  sequence.count("(") == 1:
            target = "_{}".format(variable_counter + 1)
            sequence = sequence.replace("(", "")
            sequence = sequence.replace(")", "")
            sequence = re.sub("\ +", " ", sequence)
            output.append((sequence, target))
            return target, output, variable_counter + 1
        else:
            return sequence, output, variable_counter

    def _get_target_recursively(self, sequence : str, token1 : str, token2 : str) -> str:
        if "(" in sequence:
            [function, rest] = sequence.split('(', 1)
            function = function.lstrip().rstrip()
            rest = rest.rsplit(')', 1)[0].lstrip().rstrip()
            if function == "append" or function == "prepend":
                arg1, arg2 = self._get_args(rest)
                arg1, _, _ = self._get_target_recursively(arg1, token1, token2)
                arg2, _, _ = self._get_target_recursively(arg2, token1, token2)
                if function == token1 or function == token2:
                    return getattr(self, "_" + self.replacements[function])(arg1, arg2), token1, token2
                else:
                    return getattr(self, "_" + function)(arg1, arg2), token1, token2
            else:
                rest, _, _ = self._get_target_recursively(rest, token1, token2)
                if function == token1 or function == token2:
                    return getattr(self, "_" + self.replacements[function])(rest), token1, token2
                else:
                    return getattr(self, "_" + function)(rest), token1, token2
        else:
            return sequence.split(), token1, token2

    def _get_args(self, sequence : str) -> bool:
        brackets = 0
        for i, character in enumerate(sequence):
            if character == "," and brackets == 0:
                return sequence[:i].strip(), sequence[i:].strip()[2:]
            elif character == '(': brackets += 1
            elif character == ')': brackets -= 1

    def _copy(self, string : str) -> str:
        return string

    def _reverse(self, string : str) -> str:
        return string[::-1]

    def _shift(self, string : str) -> str:
        return string[1:] + [string[0]]

    def _echo(self, string : str) -> str:
        return string + [string[-1]]

    def _append(self, string1 : str, string2 : str) -> str:
        return string1 + string2

    def _prepend(self, string1 : str, string2 : str) -> str:
        return string2 + string1

    def _place_brackets(self, seq):
        seq = seq.split()
        seq.append("END")
        queue = []
        new_seq = []

        for token in seq:
            if token == "append" or token == "prepend":
                new_seq.append(token)
                new_seq.append("(")
                queue.append(["two", 0])
            elif token in ["copy", "reverse", "shift", "echo"]:
                new_seq.append(token)
                new_seq.append("(")
                queue.append(["one", 0])
            elif token == "," or token == "END":
                while len(queue) > 0:
                    if queue[-1][0] == "one":
                        _ = queue.pop()
                        new_seq.append(")")
                    elif queue[-1][0] == "two" and queue[-1][1] == 0:
                        queue[-1][1] = 1
                        break
                    elif queue[-1][0] == "two" and queue[-1][1] == 1:
                        new_seq.append(")")
                        _ = queue.pop()
                if token == "," : new_seq.append(token)
            else:
                new_seq.append(token)

        assert new_seq.count("(") == new_seq.count(")")
        return " ".join(new_seq)