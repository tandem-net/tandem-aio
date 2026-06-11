import random

### RSA Encryptor
def is_prime(a: int) -> bool:
    if a<=1:
        return False
    if a ==2:
        return True
    if a%2 ==0:
        return False
    
    for i in range (3, int(a**0.5) + 1, 2):
        if a % i ==0:
            return False
    return True

def choose_primes():
    a = random.randint(1,100)
    prime_1 = 0
    if is_prime(a):
        prime_1 = a
    while not is_prime(a):
        a = random.randint(1,100)
        if is_prime(a):
            prime_1 = a
    return prime_1
choose_primes()

def secret_totient():
    p = choose_primes()
    q = choose_primes()
    while p ==q:
        q = choose_primes()
    n = p*q
    totient = (p-1) * (q-1)

def eucledian_algorithm():
    x = random.randint(1,100)
    y = random.randint(1,100)
    print(x, y)
    while y:
        x, y = y, (x %y)
    return x
print(eucledian_algorithm())




