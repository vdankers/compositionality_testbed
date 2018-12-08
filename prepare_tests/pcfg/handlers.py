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
        if mode == "exceptions":
            self.template = config["exceptions"]["template"]
            self.position = config["exceptions"]["position"]
            self.percentage = config["exceptions"]["percentage"]
            self.replacements = config["exceptions"]["replacements"]
            self.candidates = config["exceptions"]["candidates"]
            self.candidates1 = config["exceptions"]["candidates1"]
            self.candidates2 = config["exceptions"]["candidates2"]
        elif mode == "localism":
            self.percentage = config["localism"]["percentage"]
        elif mode == "substitutivity":
            self.percentage = config["substitutivity"]["percentage"]
            self.candidates = config["substitutivity"]["candidates"]
        elif mode == "systematicity":
            self.candidates = config["systematicity"]["candidates"]
            self.percentage = config["systematicity"]["inputs_percentage"]
            #self.inputs = config["systematicity"]["inputs"]

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
        self.binary = ["append", "prepend", "remove_first", "remove_second"]
        self.unary = ["echo", "swap_first_last", "repeat", "shift", "reverse", "copy"]
        self.functions = self.binary + self.unary
        self.letters = []
        for s in self.train:
            for t in s.source.split():
                if t.lower() != t:
                    self.letters.append(t)
        self.letters = list(set(self.letters))

    def unroll(self, sample : Sample):
        source = self._place_brackets(sample.source)
        _, unrolled_samples, _ = self._unroll_recursively(source, [], 0)
        return unrolled_samples

    def get_target(self, source : str, token1 : str, token2 : str) -> str:
        sequence = self._place_brackets(source)
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

    def replace_letters(self, sequence : str, replacements : List[str]) -> str:
        letters_to_use = list(set(self.letters) - set(replacements))
        sequence = sequence.split()
        for i, token in enumerate(sequence):
            if token in replacements:
                sequence[i] = letters_to_use[random.randint(0, len(letters_to_use)-1)]
        return " ".join(sequence)

    def keep_letters(self, sequence : str, keep : List[str]) -> str:
        sequence = sequence.split()
        for i, token in enumerate(sequence):
            if token not in keep and token not in self.functions and token != ",":
                sequence[i] = random.sample(keep, 1)[0]
        return " ".join(sequence)

    def construct_primitives(self, token : str, n : int, include_letter : str="") -> List[Sample]:
        primitives = []
        for i in range(n):
            source = [token]
            if token in self.binary:
                str1 = self._get_string(2, 5, include_letter)
                str2 = self._get_string(2, 5, include_letter)
                source = "{} {} , {}".format(token, str1, str2)
            else:
                str1 = self._get_string(2, 5, include_letter)
                source = "{} {}".format(token, str1)
            target, _, _ = self.get_target(source, None, None)
            target = " ".join(target)
            sample = Sample(source, target)
            primitives.append(sample)
        return primitives

    def _unroll_recursively(self, sequence : str,
                            output : Tuple[str, List[Tuple[str, str]], int],
                            variable_counter : int) -> \
                            (str, Tuple[str, List[Tuple[str, str]], int], int):
        if sequence.count("(") > 1:
            [function, rest] = sequence.split('(', 1)
            function = function.lstrip().rstrip()
            rest = rest.rsplit(')', 1)[0].lstrip().rstrip()
            if function in self.binary:
                arg1, arg2 = self._get_args(rest)
                target1, output, variable_counter = self._unroll_recursively(arg1, output, variable_counter)
                target2, output, variable_counter = self._unroll_recursively(arg2, output, variable_counter)
                target3 = "*{}".format(variable_counter + 1)
                output.append(("{} {} , {}".format(function, target1, target2), target3))
                return target3, output, variable_counter + 1                  
            else:
                target1, output, variable_counter = self._unroll_recursively(rest, output, variable_counter)
                target2 = "*{}".format(variable_counter + 1)
                output.append(("{} {}".format(function, target1), target2))
                return target2, output, variable_counter + 1
        elif  sequence.count("(") == 1:
            target = "*{}".format(variable_counter + 1)
            sequence = sequence.replace("(", "")
            sequence = sequence.replace(")", "")
            sequence = re.sub("\ +", " ", sequence)
            output.append((sequence, target))
            return target, output, variable_counter + 1
        else:
            return sequence, output, variable_counter

    def _get_target_recursively(self, sequence : str, token1 : str,
                                token2 : str) -> str:
        if "(" in sequence:
            [function, rest] = sequence.split('(', 1)
            function = function.lstrip().rstrip()
            rest = rest.rsplit(')', 1)[0].lstrip().rstrip()
            if function in self.binary:
                arg1, arg2 = self._get_args(rest)
                arg1, _, _ = self._get_target_recursively(arg1, token1, token2)
                arg2, _, _ = self._get_target_recursively(arg2, token1, token2)
                if function == token1 or function == token2:
                    return getattr(self, "_" + self.replacements[function])(
                            arg1, arg2
                        ), token1, token2
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

    def _place_brackets(self, seq):
        seq = seq.split()
        seq.append("END")
        queue = []
        new_seq = []

        for token in seq:
            if token in self.binary:
                new_seq.append(token)
                new_seq.append("(")
                queue.append(["two", 0])
            elif token in self.unary:
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

    def _get_string(self, min_length, max_length, include_letter=""):
        source = []
        for j in range(random.randint(min_length, max_length)):
            letter_index = random.randint(0, len(self.letters)-1)
            letter = self.letters[letter_index]
            source.append(letter)
        if include_letter is not "":
            source[random.randint(0, len(source)-1)] = include_letter
        source = " ".join(source)
        return source

    # Unary functions
    def _copy(self, sequence):
        return (sequence)

    def _reverse(self, sequence):
        return (sequence[::-1])

    def _shift(self, sequence):
        return (sequence[1:] + [sequence[0]])

    def _echo(self, sequence):
        return (sequence + [sequence[-1]])

    def _swap_first_last(self, sequence):
        return([sequence[-1]] + sequence[1:-1] + [sequence[0]])

    def _repeat(self, sequence):
        return(sequence + sequence)

    # Binary functions
    def _append(self, sequence1, sequence2):
        return (sequence1 + sequence2)

    def _prepend(self, sequence1, sequence2):
        return (sequence2 + sequence1)

    def _remove_first(self, sequence1, sequence2):
        return (sequence2)

    def _remove_second(self, sequence1, sequence2):
        return(sequence1)