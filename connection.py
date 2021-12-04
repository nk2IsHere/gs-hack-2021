import socket
from abc import ABC, abstractmethod
from typing import Dict

import requests

Args = Dict[str, any]
Data = Dict[str, any]


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
