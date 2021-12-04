from py_mini_racer import py_mini_racer

ctx = py_mini_racer.MiniRacer()

ctx.eval("let fun = () => ({ foo: 1 });")
print(ctx.call("fun"))