import os


class Cache:
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            # 1. Get the cache key
            key = str(hash((args, kwargs)))
            # 2. Check if the cache key exists
            if os.path.exists(os.path.join(self.cache_dir, key)):
                with open(os.path.join(self.cache_dir, key)) as cache_file:
                    return cache_file.read()
            # 3. If the cache key doesn't exist, call the function and write the result to the cache
            result = func(*args, **kwargs)
            with open(os.path.join(self.cache_dir, key), "w") as cache_file:
                cache_file.write(result)
            return result

        return wrapper
