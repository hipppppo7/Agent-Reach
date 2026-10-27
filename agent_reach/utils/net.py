"""TLS trust for urllib: the OS store plus certifi's Mozilla bundle.

On Windows, Python loads the system store as is. A store that holds only the
cross-signed "USERTrust ECC" (issued by AAA Certificate Services) fails
GitHub's Sectigo E46 chain with "unable to get issuer certificate", while
browsers fetch the missing root on demand. Adding certifi (already installed
with requests) gives OpenSSL the self-signed root and keeps any corporate CA
from the OS store.
"""
import ssl
from functools import lru_cache


@lru_cache(maxsize=1)
def ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    try:
        import certifi

        ctx.load_verify_locations(certifi.where())
    except (ImportError, OSError, ssl.SSLError):
        pass
    return ctx
