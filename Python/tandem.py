import cloudpickle
import requests

port = 6767
address = "http://localhost:" + str(port)

def split(func, args):
    # Validate inputs
    if not type(args) == list:
        raise TypeError("args must be a list")
    if len(args) == 0:
        raise ValueError("args must not be empty")
    if not callable(func):
        raise TypeError("func must be a function")
    
    # Serialize
    serial_func = cloudpickle.dumps(func)
    serial_args = cloudpickle.dumps(args)
    
    # Server
    response = requests.post(address + "/execute", data={
        "func": serial_func,
        "args": serial_args
    })
    
    # Deserialize
    result = cloudpickle.loads(response.content)
    return result