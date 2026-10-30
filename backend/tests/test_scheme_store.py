from app.services import scheme_store


def test_mongo_client_is_reused_and_closed(monkeypatch) -> None:
    class FakeClient:
        closed = False

        def close(self) -> None:
            self.closed = True

    clients: list[FakeClient] = []

    def create_client(uri: str) -> FakeClient:
        assert uri == "mongodb+srv://example.invalid"
        client = FakeClient()
        clients.append(client)
        return client

    monkeypatch.setenv("MONGODB_URI", "mongodb+srv://example.invalid")
    monkeypatch.setattr(scheme_store, "MongoClient", create_client)
    monkeypatch.setattr(scheme_store, "_mongo_client", None)
    try:
        first_client = scheme_store._get_mongo_client()
        second_client = scheme_store._get_mongo_client()

        assert first_client is second_client
        assert len(clients) == 1
    finally:
        scheme_store.close_mongo_client()

    assert clients[0].closed
