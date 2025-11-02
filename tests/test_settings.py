def test_azure_settings(monkeypatch):
    monkeypatch.setenv("AZURE_ACCOUNT_NAME", "localdev")
    monkeypatch.setenv("AZURE_ACCOUNT_KEY", "test-key")
    monkeypatch.setenv("AZURE_CONTAINER", "test-container")

    from larvixon_site import settings

    assert settings.AZURE_ACCOUNT_NAME == "localdev"
    assert settings.AZURE_ACCOUNT_KEY == "test-key"
    assert settings.AZURE_CONTAINER == "test-container"
