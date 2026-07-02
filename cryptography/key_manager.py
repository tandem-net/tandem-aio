from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature
import os
from cryptography.hazmat.primitives import serialization
#Node A's private and public key
private_key1 = ed25519.Ed25519PrivateKey.generate()
print(f"The private key is HIDDEN")
public_key1 = private_key1.public_key()
public_key_bites1 = public_key1.public_bytes(encoding = serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)
print(f"The public key is {public_key_bites1}")

#Node B's private and public key
private_key2 = ed25519.Ed25519PrivateKey.generate()
print(f"The private key is HIDDEN")
public_key2 = private_key2.public_key()
public_key_bites2 = public_key2.public_bytes(encoding = serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)
print(f"The public key is {public_key_bites2}")



#Node B's message
message = os.urandom(16)
#Triggers the Ed25519 cryptographic algorithm. Hashes the
#message combined with a random hidden number and multiplies
#it by the private key
signature = private_key1.sign(message)
print(f"Signature (hex): {signature.hex()}")

#Verify the signature
try:
    public_key1.verify(signature, message)
    print("Verification passed!")
except InvalidSignature:
    print("Verification failed")

try:
    public_key2.verify(signature, message)
    print("Verification passed!")
except InvalidSignature:
    print("Verification failed")
