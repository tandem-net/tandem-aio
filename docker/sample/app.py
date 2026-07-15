import tandem


@tandem.compute(batch=1, timeout_ms=5000)
def crunch(n):
    total = 0
    for i in range(n):
        total += i
    return total
