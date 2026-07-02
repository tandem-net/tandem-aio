import tandem

num = tandem.Immutable(5)

@tandem.compute(batch=3, timeout_ms=50)
def foo(x): 
    return x * 2

print(num)
print(foo(num.value))

goo = tandem.split(foo, 2)

print(goo([1, 2, 3, 4, 5]))