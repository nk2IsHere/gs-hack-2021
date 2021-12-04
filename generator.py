from abc import ABC, abstractmethod
from plistlib import Dict
from random import random

from executor import Args
from test import TestMetadata


class Generator(ABC):
  def __init__(self, args: Args):
    self.args = args

  @abstractmethod
  def next(self, test_metadata: TestMetadata) -> T:
    pass


Data = Dict[str, Generator]


class FileGenerator(Generator):
  def __init__(self, args: Args):
    super(FileGenerator, self).__init__(args)
    path = self.args['path']
    split = self.args['split']

    with open(path) as f:
      self.lines = f.read().split(split if split != 'newline' else '\n')

  def next(self, test_metadata: TestMetadata) -> str:
    return self.lines[test_metadata.current_position % len(self.lines)]


class RNGenerator(Generator):

  def __init__(self, args: Args):
    super(RNGenerator, self).__init__(args)

  def next(self, test_metadata: TestMetadata) -> any:
    return random.randint(self.args['min'], self.args['max'])


class ConstantGenerator(Generator):

  def next(self, test_metadata: TestMetadata) -> any:
    return self.args['value']
