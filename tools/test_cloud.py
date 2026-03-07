from lib.cloud_client import CloudClient

def test_cloud_unavailable():
    # We do not have OPENROUTER_API_KEY in test by default, so it should be unavailable.
    cc = CloudClient()
    if not cc.api_key:
        assert not cc.is_available(), "CloudClient should be unavailable without key"
    print("Success: test_cloud passed.")

if __name__ == "__main__":
    test_cloud_unavailable()
