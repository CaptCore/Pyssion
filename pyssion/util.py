import random
import string

def generate_random_string():
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(6))