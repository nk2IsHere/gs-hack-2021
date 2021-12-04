import json
import re
from collections import namedtuple
from typing import TextIO, Dict, Tuple, List
from math import isclose


def load(fp: TextIO) -> Dict[str, object]:
  return loads(fp.read())


LessThanEqual = namedtuple('LessThanEqual', ['value'])
LessThan = namedtuple('LessThan', ['value'])
MoreThanEqual = namedtuple('MoreThanEqual', ['value'])
MoreThan = namedtuple('MoreThan', ['value'])
Equal = namedtuple('Equal', ['value'])
NotEqual = namedtuple('NotEqual', ['value'])

Milliseconds = namedtuple('Milliseconds', ['value'])
Seconds = namedtuple('Seconds', ['value'])
Minutes = namedtuple('Minutes', ['value'])
Hours = namedtuple('Hours', ['value'])

NamedNumber = namedtuple('NamedNumber', ['name', 'value'])

Percentage = namedtuple('Percentage', ['value'])


def _parse_value(value: str) -> object:
  if re.match('([-]?[0-9]+[,.]?[0-9]*([\/][0-9]+[,.]?[0-9]*)*)$', value):
    if '/' in value:
      return float(value.split('/')[0]) / float(value.split('/')[1])
    else:
      return float(value)

  if re.match('^((100)|(\d{1,2}(.\d*)?))%$', value):
    return Percentage(float(value[:-1]))

  strippedValue = ''.join(value.split())
  if '<=' == strippedValue[:2]:
    return LessThanEqual(_parse_value(strippedValue[2:]))
  if '>=' == strippedValue[:2]:
    return MoreThanEqual(_parse_value(strippedValue[2:]))
  if '<' == strippedValue[:1]:
    return LessThan(_parse_value(strippedValue[1:]))
  if '>' == strippedValue[:1]:
    return MoreThan(_parse_value(strippedValue[1:]))
  if '=' == strippedValue[:1]:
    return Equal(_parse_value(strippedValue[1:]))

  namedNumber = re.match('^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?', value)
  if namedNumber:
    if not re.match('^[a-zA-Z]+$', value[namedNumber.span()[1] + 1:]):
      return value
    return NamedNumber(value[namedNumber.span()[1] + 1:], float(value[:namedNumber.span()[1]]))

  # print(f'Unknown value: {value}')
  return value


def _parse_line(line: str) -> Tuple[str, object]:
  return line.split(':')[0].rstrip(), _parse_value(line.split(':')[1].lstrip())


def _walk_set(dict: Dict[str, object], path: List[str], value: object):
  path = path[::-1]
  while len(path) > 1:
    val = path.pop()
    if val not in dict:
      dict[val] = {}

    dict = dict[val]
    if not isinstance(dict, Dict):
      return

  dict[path[0]] = value


def loads(input: str) -> Dict[str, object]:
  currentLine = 0
  overallIdent = 0

  previousDepth = 0
  currentDepth = 0
  nextIdentShouldDiffer = False

  tree = {}
  currentPath = []

  for line in input.split('\n'):
    if len(line.lstrip()) == 0:
      continue

    line = line.rstrip()
    ident = len(line) - len(line.lstrip())

    if currentLine == 0 and ident != 0:
      raise Exception('Root cannot start from ident')

    if overallIdent == 0:
      overallIdent = ident

    if ident != 0 and not isclose(ident / overallIdent, ident // overallIdent):
      raise Exception('Ident cannot be less than first ever spotted ident')

    previousDepth = currentDepth
    currentDepth = ident // overallIdent if ident != 0 else 0

    line = line.lstrip()
    key, value = _parse_line(line)

    if previousDepth == currentDepth and nextIdentShouldDiffer:
      raise Exception('Key has no value')

    if value == '' and not nextIdentShouldDiffer:
      nextIdentShouldDiffer = True

    if value != '':
      nextIdentShouldDiffer = False

    if previousDepth > currentDepth:
      # print(f"pop {currentPath} {previousDepth - currentDepth}")
      for i in range(previousDepth - currentDepth):
        currentPath.pop()

    # print(previousDepth, currentDepth, key, value, currentPath)

    if value != '':
      _walk_set(tree, currentPath + [key], value)
    else:
      currentPath.append(key)

    currentLine += 1

  return tree


if __name__ == '__main__':
  print(json.dumps(loads('''
connection: python-server

data:
    path:
        type: constant value
        value: /demo/endpoint
    query:
        type: file read generator
        path: ./data-input.txt
        split: \\n
    output:
        type: file read generator
        path: ./data-output.txt
        split: \\n

protocol:
    type: http
    method: GET
    path: path
    query: query


test:
    type: reliability
    validation:
        error rate: 1/1000
        output: output
    execution:
        repetition count: 50000
        requests in parallel count: 10
''')))
  print(loads('''
connection: fib
data:
    number:
        type: random number generator
        min: 0
        max: 1000000
        key: number

protocol:
    type: binary plain
    input: number

test:
    type: performance
    validation:
        cpu: <=50%
        response time: <= 5ms
        throughput: 5000 rps
    execution:
        warmup runs count: 250
        iterations: 1000
        batches: 100'''))
  print(loads('''
connections:
  python-server:
      type: http
      ip: 127.0.0.1
      port: 5000'''))
