import glob
import json
import os
import random
import sys
import time
from abc import ABC, abstractmethod
from collections import namedtuple
from enum import Enum, auto
from typing import Dict, TypeVar, Tuple, List
import socket
import requests

from parser import load

T = TypeVar('T')
R = TypeVar('R')

ExecutorMetrics = Dict[str, T]
Args = Dict[str, any]


class ExecutorRunningConfig(ABC):

  @abstractmethod
  def before(self) -> ExecutorMetrics:
    pass

  @abstractmethod
  def delta(self, initial_metrics: ExecutorMetrics) -> ExecutorMetrics:
    pass


class Connection(ABC):

  def __init__(self, args: Args):
    self.args = args

  @abstractmethod
  def send(self, input: any) -> any:
    pass


class TcpConnection(Connection):

  def __init__(self, args: Args):
    super().__init__(args)

  def send(self, input: bytes) -> bytes:
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    address = (self.args['ip'], int(self.args['port']))
    soc.connect(address)
    soc.sendall(input)

    return soc.recv(2000)


class HttpConnection(Connection):

  def __init__(self, args: Args):
    super().__init__(args)

  def send(self, input: Dict[str, any]) -> str:
    r = requests.request(
      method=input['method'],
      url=f"http://{self.args['ip']}:{int(self.args['port'])}{input['path']}",
      params=input['query'] if 'query' in input else None,
      data=input['data'] if 'data' in input else None,
    )

    return r.text


ExecutionResult = namedtuple('ExecutionResult', ['output', 'metrics'])


class TestMetadata:

  def __init__(self, current_position: int):
    self.current_position = current_position


class Generator(ABC):
  def __init__(self, args: Args):
    self.args = args

  @abstractmethod
  def next(self, test_metadata: TestMetadata) -> T:
    pass


Data = Dict[str, Generator]


class Protocol(ABC):

  def __init__(self, args: Args):
    self.args = args

  @abstractmethod
  def input(self, data: Data, test_metadata: TestMetadata) -> T:
    pass

  @abstractmethod
  def output(self, data: any) -> R:
    pass


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

  def next(self, test_metadata: TestMetadata) -> T:
    return random.randint(self.args['min'], self.args['max'])


class ConstantGenerator(Generator):

  def next(self, test_metadata: TestMetadata) -> T:
    return self.args['value']


class AsciiProtocol(Protocol):

  def input(self, data: Data, test_metadata: TestMetadata) -> bytes:
    return str(data[self.args['input']].next(test_metadata)).encode('ascii')

  def output(self, data: bytes) -> str:
    return data.decode('ascii')


class HttpProtocol(Protocol):
  def input(self, data: Data, test_metadata: TestMetadata) -> T:
    return {
      "method": self.args['method'],
      "path": data[self.args['path']].next(test_metadata),
      "query": json.loads(data[self.args['query']].next(test_metadata) if 'query' in data else None),
      "body": data[self.args['body']].next(test_metadata) if 'body' in data else None,
    }

  def output(self, data: any) -> any:
    return str(data)


class Executor:

  def __init__(self, protocol: Protocol, connection: Connection):
    self.protocol = protocol
    self.connection = connection

  def run(self, data: Data, running_config: ExecutorRunningConfig, test_metadata: TestMetadata) -> ExecutionResult:
    metrics = running_config.before()
    output = self.protocol.output(self.connection.send(self.protocol.input(data, test_metadata)))
    metrics = running_config.delta(metrics)

    return ExecutionResult(output, metrics)


class TestResultState(Enum):
  success = auto()
  failed = auto()


TestResult = namedtuple('TestResult', ['output', 'metric', 'state'])


class Test(ABC):

  def __init__(self, data: Data, executor_running_config: ExecutorRunningConfig,
               args: Args):
    self.data = data
    self.test_metadata = TestMetadata(0)
    self.executor_running_config = executor_running_config
    self.args = args
    pass

  @abstractmethod
  def run(self, executor: Executor) -> [TestResult]:
    pass


class ReliabilityTestExecutorRunningConfig(ExecutorRunningConfig):

  def before(self) -> ExecutorMetrics:
    pass

  def delta(self, initial_metrics: ExecutorMetrics) -> ExecutorMetrics:
    pass


class ReliabilityTest(Test):
  def __init__(self, data: Data, args: Args):
    super().__init__(data, ReliabilityTestExecutorRunningConfig(), args)
    self.error_count = 0
    self.request_count = int(self.args['execution']['repetition count'])
    self.error_rate = self.args['validation']['error rate']

  def _validate_result_get_state(self, output: R, metrics: ExecutorMetrics) -> TestResultState:
    next_expected_output = self.data['output'].next(self.test_metadata)
    is_same = next_expected_output == output
    if not is_same:
      self.error_count += 1

    return TestResultState.success if is_same else TestResultState.failed

  def run(self, executor: Executor) -> List[TestResult]:
    res = []
    for i in range(self.request_count):
      output, metrics = executor.run(self.data, self.executor_running_config, self.test_metadata)
      validation_result = self._validate_result_get_state(output, metrics)
      self.test_metadata.current_position += 1
      res.append(TestResult(output, metrics, validation_result))
    return [TestResult(
      res,
      {
        'error_count': self.error_count,
        'error_rate': self.error_count / self.request_count,
        'test_passed': self.error_count / self.request_count <= self.error_rate
      },
      TestResultState.success
      if self.error_count / self.request_count <= self.error_rate
      else TestResultState.failed
    )]


class PerformanceTestExecutorRunningConfig(ExecutorRunningConfig):

  def before(self) -> ExecutorMetrics:
    return {'start_time': time.time()}

  def delta(self, initial_metrics: ExecutorMetrics) -> ExecutorMetrics:
    return {'execution_time': time.time() - initial_metrics['start_time']}


class PerformanceTest(Test):
  def __init__(self, data: Data, args: Args):
    super().__init__(data, PerformanceTestExecutorRunningConfig(), args)
    self.warmup_count = int(self.args['execution']['warmup runs count'])
    self.iterations = int(self.args['execution']['iterations'])
    self.batches = int(self.args['execution']['batches'])

    self.response_time = int(self.args['validation']['response time'][0][1]) * 1000
    self.throughput = int(self.args['validation']['throughput'][1])

  def _validate_result_get_state(self, metrics: ExecutorMetrics) -> TestResultState:
    return TestResultState.success \
      if metrics['avg_response_time'] <= self.response_time and metrics['throughput'] >= self.throughput \
      else TestResultState.failed

  def run(self, executor: Executor) -> List[TestResult]:
    print('Performance test warming up')
    warmup_output = []
    warmup_total_time = 0
    for i in range(self.warmup_count):
      output, metrics = executor.run(self.data, self.executor_running_config, self.test_metadata)
      warmup_total_time += metrics['execution_time']
      warmup_output.append(output)

    warmup_metrics = {
      'avg_response_time': warmup_total_time / self.warmup_count,
      'throughput': int(self.warmup_count / warmup_total_time)
    }
    print(f'Metrics for warming up: {warmup_metrics}')

    print('Performance test main load')
    total_avg_response_time = 0
    for batch in range(self.batches):
      current_batch_output = []
      current_batch_total_time = 0
      for i in range(self.iterations):
        output, metrics = executor.run(self.data, self.executor_running_config, self.test_metadata)
        current_batch_total_time += metrics['execution_time']
        current_batch_output.append(output)

      current_batch_metrics = {
        'avg_response_time': current_batch_total_time / self.iterations,
        'throughput': int(self.iterations / current_batch_total_time)
      }
      total_avg_response_time += current_batch_total_time / self.iterations

      print(f'Metrics for current batch {batch}: {current_batch_metrics}')

    overall_metrics = {
      'avg_response_time': total_avg_response_time / self.batches,
      'throughput': int(self.batches / total_avg_response_time)
    }
    self.test_metadata.current_position += 1
    return [TestResult(
      None,
      overall_metrics,
      self._validate_result_get_state(overall_metrics)
    )]


class TestRunner:

  def __init__(self, connection: Connection, data: Data, protocol: Protocol, test: Test):
    self.connection = connection
    self.data = data
    self.protocol = protocol
    self.test = test

  def execute(self) -> [TestResult]:
    executor = Executor(self.protocol, self.connection)
    return self.test.run(executor)


connectionsByType = {
  "tcp": TcpConnection,
  "http": HttpConnection
}

generatorsByType = {
  "random number generator": RNGenerator,
  "file read generator": FileGenerator,
  "constant value": ConstantGenerator
}

protocolByName = {
  "ascii plain": AsciiProtocol,
  "http": HttpProtocol
}

testByName = {
  "performance": PerformanceTest,
  "reliability": ReliabilityTest
}

if __name__ == "__main__":
  tests_folder_path = sys.argv[1]
  env_path = sys.argv[2]

  if not os.path.isdir(tests_folder_path):
    raise Exception("Tests argument not a folder")

  if not os.path.isfile(env_path):
    raise Exception("Env argument not a file")

  with open(env_path) as env_file:
    environment = load(env_file)

  for generator_file_name in glob.glob('*.bbgen'):
    print(f"Instantiating generator: {generator_file_name.replace('.bbgen', '')}")
    # TODO: actually instantiate it

  connections = {}
  for name, connection in environment['connections'].items():
    connections[name] = connectionsByType[connection['type']](connection)

  tests = {}
  for test_file_name in os.listdir(tests_folder_path):
    with open(os.path.join(tests_folder_path, test_file_name)) as test_file:
      test_config = load(test_file)
      # print(json.dumps(test_config))
      data = {
        key: generatorsByType[generator_config['type']](generator_config)
        for key, generator_config in test_config['data'].items()
      }
      tests[test_file_name] = TestRunner(
        connection=connections[test_config['connection']],
        data=data,
        protocol=protocolByName[test_config['protocol']['type']](test_config['protocol']),
        test=testByName[test_config['test']['type']](data, test_config['test']),
      )

  for name, test in tests.items():
    print(f'Executing test {name}')
    result = test.execute()
    output, metrics, state = result[0]
    print(f'Got result, metrics: {metrics}, state: {state}')
