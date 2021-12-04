import glob
import os
import sys

from connection import TcpConnection, HttpConnection
from generator import RNGenerator, FileGenerator, ConstantGenerator
from parser import load
from protocol import AsciiProtocol, HttpProtocol
from test import PerformanceTest, ReliabilityTest
from test_runner import TestRunner

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
  project_folder_path = sys.argv[1]

  if not os.path.isdir(project_folder_path):
    raise Exception("Project argument not a folder")

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
