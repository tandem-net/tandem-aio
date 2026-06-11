import random

### RSA Encryptor
def is_prime(a: int) -> bool:
    if a<1:
        return False
    if a==1:
        return True
    if a ==2:
        return True
    if a%2 ==0:
        return False
    
    for i in range (3, int(a**0.5) + 1, 2):
        if a % i ==0:
            return False
    return True

random_number1 = random.randint(1,100)
random_number2 = random.randint(1,100)
if is_prime(random_number1):
    prime_1 = random_number1
if is_prime(random_number2):
    prime_2 = random_number2
print(prime_1)
print(prime_2)


