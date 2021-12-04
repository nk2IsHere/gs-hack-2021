import glob
import os
import sys

from connection import TcpConnection, HttpConnection
from generator import RNGenerator, FileGenerator, ConstantGenerator, JavaScriptGenerator
from parser import load
from protocol import AsciiProtocol, HttpProtocol
from test import PerformanceTest, ReliabilityTest
from test_runner import TestRunner

connectionsByType = {
  "tcp": TcpConnection,
  "http": HttpConnection
}

generatorsByType = {
  # "random number generator": RNGenerator,
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

connections = {}
tests = {}


def install_generator(code, file_name):
  print(f"Instantiating generator: {file_name}")
  generatorsByType[file_name.replace('.bbgen', '')] = lambda args: JavaScriptGenerator(args, code)


def install_test(content, file_name):
  test_config = load(content)
  data = {
    key: generatorsByType[generator_config['type']](generator_config)
    for key, generator_config in test_config['data'].items()
  }
  tests[file_name] = TestRunner(
    connection=connections[test_config['connection']],
    data=data,
    protocol=protocolByName[test_config['protocol']['type']](test_config['protocol']),
    test=testByName[test_config['test']['type']](data, test_config['test']),
  )


if __name__ == "__main__":
  project_folder_path = sys.argv[1]

  if not os.path.isdir(project_folder_path):
    raise Exception("Project argument not a folder")

  files = os.listdir(project_folder_path)

  env_files = [file for file in files if file.split('.') == 'bbenv']
  test_files = [file for file in files if file.split('.') == 'bbtest']
  gen_files = [file for file in files if file.split('.') == 'bbtest']

  if len(env_files) != 1:
    raise Exception("Project needs exactly one bbenv file")

  with open(os.path.join(project_folder_path, env_files[0])) as env_file:
    environment = load(env_file)

  for file_name in gen_files:
    with open(os.path.join(project_folder_path, file)) as file:
      install_generator(file.read(), file_name)

  for name, connection in environment['connections'].items():
    connections[name] = connectionsByType[connection['type']](connection)

  for test_file_name in test_files:
    with open(os.path.join(project_folder_path, test_file_name)) as file:
      install_test(file.read(), test_file_name)

  for name, test in tests.items():
    print(f'Executing test {name}')
    result = test.execute()
    output, metrics, state = result[0]
    print(f'Got result, metrics: {metrics}, state: {state}')
