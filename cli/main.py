import os
import cloudpickle

# Define the overall target range
LIMIT = 1000000000
NUM_CHUNKS = 10
CHUNK_SIZE = LIMIT // NUM_CHUNKS

# Ensure the directory exists to receive the pickles
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pickles")
os.makedirs(output_dir, exist_ok=True)

# This worker function holds the actual prime calculation logic
def calculate_prime_product_range(start, end):
    import math
    
    def is_prime(n):
        if n < 2:
            return False
        for i in range(2, int(math.isqrt(n)) + 1):
            if n % i == 0:
                return False
        return True

    product = 1
    # Adjust start slightly to avoid checking 0 or 1
    actual_start = max(2, start)
    
    for num in range(actual_start, end):
        if is_prime(num):
            product *= num
            
    return product

# Generate the 10 separate chunk pickles
for i in range(NUM_CHUNKS):
    start_range = i * CHUNK_SIZE
    end_range = (i + 1) * CHUNK_SIZE
    
    # Bundle the function alongside its unique range arguments 
    # using a lambda closure so the worker knows exactly what slice to execute
    task_closure = lambda s=start_range, e=end_range: calculate_prime_product_range(s, e)
    
    pickle_filename = f"prime_chunk_{i + 1}.pkl"
    pickle_path = os.path.join(output_dir, pickle_filename)
    
    with open(pickle_path, "wb") as f:
        cloudpickle.dump(task_closure, f)
        
    print(f"Created executable pickle: {pickle_path} for range {start_range} to {end_range}")
