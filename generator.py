from abc import ABC, abstractmethod
from random import random
from typing import Dict
import execjs

# from executor import Args
from test import TestMetadata

Args = Dict[str, any]


class Generator(ABC):
  def __init__(self, args: Args):
    self.args = args

  @abstractmethod
  def next(self, test_metadata: TestMetadata) -> any:
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


class JavaScriptGenerator(Generator):
  def __init__(self, args: Args, code: str):
    super(JavaScriptGenerator, self).__init__(args)
    self.ctx = execjs.compile(code)

  def next(self, test_metadata: TestMetadata) -> any:
    return self.ctx.call('generator', self.args, test_metadata.__dict__)