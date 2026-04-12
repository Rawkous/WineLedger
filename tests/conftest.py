import os
import tempfile


def pytest_configure(config):
    if os.environ.get("WINLEDGER_CHAIN_PATH"):
        return
    d = tempfile.mkdtemp(prefix="wineledger_test_")
    os.environ["WINLEDGER_CHAIN_PATH"] = os.path.join(d, "chain.json")
