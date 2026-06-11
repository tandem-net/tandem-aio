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
    return n, totient

def eucledian_algorithm(x,y):
    print(x, y)
    while y:
        x, y = y, (x %y)
    return x

e = 3
n, totient = secret_totient()
public_key_exponent = 0
while e<totient:
    gcd_result = eucledian_algorithm(e, totient)
    if gcd_result !=1:
        e+=2
    else:
        break

def private_key_exponent(e, totient):
    d = 1
    while True:
        if (d * e) % totient !=1:
            d+=1
        else:
            return d
        
def encrypt(message, e, n):
    return pow(message, e, n)

def decrypt(ciphertext, d, n):
    return pow(ciphertext, d, n)
    
n, totient = secret_totient()
d = private_key_exponent(e, totient)

print(f"Public Key: (e={e}, n={n})")
print(f"Private Key: (d={d}, n={n})")

original_msg = 12
print(f"\nOriginal Message: {original_msg}")

encrypted_msg = encrypt(original_msg, e, n)
print(f"Encrypted Ciphertext: {encrypted_msg}")

decrypted_msg = decrypt(encrypted_msg, d, n)
print(f"Decrypted Result: {decrypted_msg}")