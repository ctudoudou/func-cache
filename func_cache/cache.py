from json import dumps, loads
import os
from inspect import signature
from logging import getLogger
import dis
import hashlib

logger = getLogger(__name__)


class RedisCache:
    def __init__(
        self,
        unix_socket_path=None,
        encoding="utf-8",
        encoding_errors="strict",
        charset=None,
        uri=None,
    ):
        import redis

        if uri:
            self.redis = redis.Redis.from_url(uri)
        elif unix_socket_path:
            self.redis = redis.Redis(
                unix_socket_path=unix_socket_path,
                encoding=encoding,
                encoding_errors=encoding_errors,
                charset=charset,
            )
        else:
            raise ValueError("Either uri or unix_socket_path must be provided")

    def get(self, key):
        return self.redis.get(key)

    def set(self, key, value, ex=None):
        self.redis.set(key, value, ex=ex)


class MemcachedCache:
    def __init__(self, servers=None, default_timeout=300):
        import pylibmc

        if servers is None:
            raise ValueError("servers must be provided")
        self.mc = pylibmc.Client(servers, binary=True)
        self.default_timeout = default_timeout

    def get(self, key):
        return self.mc.get(key)

    def set(self, key, value, ex=None):
        self.mc.set(key, value, time=ex)


class Cache:
    def __init__(self, engine="file", cache_dir=".cache", prefix="", key_digest_size=8):
        logger.info(f"Using {engine} engine")
        if engine == "file":
            logger.info(f"Using {cache_dir} as cache directory")
            os.makedirs(cache_dir, exist_ok=True)
        self.cache_dir = cache_dir
        self.prefix = prefix
        self.key_digest_size = key_digest_size

    @staticmethod
    def get_args(fn, args, kwargs):
        """
        This function parses the args and kwargs in the context of a function and creates unified
        dictionary of {<argument_name>: <value>}. This is useful
        because arguments can be passed as args or kwargs, and we want to make sure we cache
        them both the same. Otherwise there would be different caching for add(1, 2) and add(arg1=1, arg2=2)
        """
        arg_sig = signature(fn)
        standard_args = [
            param.name
            for param in arg_sig.parameters.values()
            if param.kind is param.POSITIONAL_OR_KEYWORD
        ]
        allowed_kwargs = {
            param.name
            for param in arg_sig.parameters.values()
            if param.kind is param.POSITIONAL_OR_KEYWORD
            or param.kind is param.KEYWORD_ONLY
        }
        variable_args = [
            param.name
            for param in arg_sig.parameters.values()
            if param.kind is param.VAR_POSITIONAL
        ]
        variable_kwargs = [
            param.name
            for param in arg_sig.parameters.values()
            if param.kind is param.VAR_KEYWORD
        ]
        parsed_args = {}

        if standard_args or variable_args:
            for index, arg in enumerate(args):
                try:
                    parsed_args[standard_args[index]] = arg
                except IndexError:
                    # then fallback to using the positional varargs name
                    if variable_args:
                        args_name = variable_args[0]
                        if args_name not in parsed_args:
                            parsed_args[args_name] = []

                        parsed_args[args_name].append(arg)

        if kwargs:
            for key, value in kwargs.items():
                if key in allowed_kwargs:
                    parsed_args[key] = value
                elif variable_kwargs:
                    kwargs_name = variable_kwargs[0]
                    if kwargs_name not in parsed_args:
                        parsed_args[kwargs_name] = {}
                    parsed_args[kwargs_name][key] = value

        return parsed_args

    def get_prefix(self):
        return self.prefix

    def pickle(self, obj):
        return dumps(obj, separators=(",", ":"))

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            # 1. Get the cache key
            key = (
                self.get_prefix()
                + func.__module__
                + func.__qualname__
                + str(self.get_args(func, args, kwargs))
            ) + "."
            key += hashlib.blake2s(
                str(dis.code_info(func)).encode(), digest_size=self.key_digest_size
            ).hexdigest()

            # 2. Check if the cache key exists
            if os.path.exists(os.path.join(self.cache_dir, key)):
                with open(os.path.join(self.cache_dir, key)) as cache_file:
                    try:
                        return loads(cache_file.read())
                    except Exception as e:
                        logger.error(f"Error loading cache file {key}: {e}")
                        os.remove(os.path.join(self.cache_dir, key))

            # 3. If the cache key doesn't exist, call the function and write the result to the cache
            result = func(*args, **kwargs)
            try:
                with open(os.path.join(self.cache_dir, key), "w") as cache_file:
                    cache_file.write(self.pickle(result))
            except Exception as e:
                logger.error(f"Error writing cache file {key}: {e}")

            return result

        return wrapper
