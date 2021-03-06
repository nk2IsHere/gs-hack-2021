from abc import ABC, abstractmethod
from collections import namedtuple
from typing import Dict

from connection import Connection
from protocol import Protocol
from test_metadata import TestMetadata

ExecutionResult = namedtuple('ExecutionResult', ['output', 'metrics'])
ExecutorMetrics = Dict[str, any]
Args = Dict[str, any]
Data = Dict[str, any]


class ExecutorRunningConfig(ABC):

  @abstractmethod
  def before(self) -> ExecutorMetrics:
    pass

  @abstractmethod
  def delta(self, initial_metrics: ExecutorMetrics) -> ExecutorMetrics:
    pass


class Executor:

  def __init__(self, protocol: Protocol, connection: Connection):
    self.protocol = protocol
    self.connection = connection

  def run(self, data: Data, running_config: ExecutorRunningConfig, test_metadata: TestMetadata) -> ExecutionResult:
    input = self.protocol.input(data, test_metadata)
    metrics = running_config.before()
    output_raw = self.connection.send(input)
    metrics = running_config.delta(metrics)
    output = self.protocol.output(output_raw)

    return ExecutionResult(output, metrics)
