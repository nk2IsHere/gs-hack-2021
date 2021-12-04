import json
from abc import ABC, abstractmethod
from typing import Dict

from test_metadata import TestMetadata

Args = Dict[str, any]
Data = Dict[str, any]


class Protocol(ABC):

  def __init__(self, args: Args):
    self.args = args

  @abstractmethod
  def input(self, data: Data, test_metadata: TestMetadata) -> any:
    pass

  @abstractmethod
  def output(self, data: any) -> any:
    pass


class AsciiProtocol(Protocol):

  def input(self, data: Data, test_metadata: TestMetadata) -> bytes:
    return str(data[self.args['input']].next(test_metadata)).encode('ascii')

  def output(self, data: bytes) -> str:
    return data.decode('ascii')


class HttpProtocol(Protocol):
  def input(self, data: Data, test_metadata: TestMetadata) -> any:
    return {
      "method": self.args['method'],
      "path": data[self.args['path']].next(test_metadata),
      "query": json.loads(data[self.args['query']].next(test_metadata) if 'query' in data else None),
      "body": data[self.args['body']].next(test_metadata) if 'body' in data else None,
    }

  def output(self, data: any) -> any:
    return str(data)
