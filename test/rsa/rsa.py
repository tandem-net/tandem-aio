import sympy
import random

p = sympy.randprime(1000, 10000)
q = sympy.randprime(1000, 10000)
while p == q:
    q = sympy.randprime(1000, 10000)
    
n = p * q
totient = (p - 1) * (q - 1)

e = 3
while sympy.gcd(e, totient) != 1:
    e += 2

public = (e, n)

# private = sympy.mod_inverse(e, totient)

def extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    gcd, x1, y1 = extended_gcd(b % a, a)
    x = y1 - (b // a) * x1
    y = x1
    return gcd, x, y

def mod_inverse(e, totient):
    gcd, x, y = extended_gcd(e, totient)
    return x % totient
    
    
private = mod_inverse(e, totient)


message = 156231
ciphertext = pow(message, public[0], public[1])
decrypted_message = pow(ciphertext, private, public[1])

print(f"p: {p}, q: {q}")
print(f"Public Key: (e={public[0]}, n={public[1]})")
print(f"Private Key: (d={private}, n={public[1]})")
print(f"Original Message: {message}")
print(f"Ciphertext: {ciphertext}")
print(f"Decrypted Message: {decrypted_message}")