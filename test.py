from abc import ABC, abstractmethod
from collections import namedtuple
from datetime import time
from enum import Enum, auto
from typing import List, Dict

from executor import Executor, ExecutorMetrics, Args, ExecutorRunningConfig
# from generator import Data
from test_metadata import TestMetadata

Data = Dict[str, any]


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

  def _validate_result_get_state(self, output: any, metrics: ExecutorMetrics) -> TestResultState:
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
