import tandem

@tandem.compute
def hello():
    return 'Hello from deployed version'

print('Running version 1')
