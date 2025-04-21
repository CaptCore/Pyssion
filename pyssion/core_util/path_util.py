import random
import string
import os

def generate_random_string():
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(6))

def generate_pyssion_cache_file(cache_dir:str):
    cachename = os.path.join(generate_random_string(),".pyssioncache")
    cache_full_path = os.path.join(cache_dir,cachename)
    return cache_full_path
