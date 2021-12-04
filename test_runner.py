from connection import Connection
from executor import Executor
from generator import Data
from protocol import Protocol
from test import TestResult, Test


class TestRunner:

  def __init__(self, connection: Connection, data: Data, protocol: Protocol, test: Test):
    self.connection = connection
    self.data = data
    self.protocol = protocol
    self.test = test

  def execute(self) -> [TestResult]:
    executor = Executor(self.protocol, self.connection)
    return self.test.run(executor)
