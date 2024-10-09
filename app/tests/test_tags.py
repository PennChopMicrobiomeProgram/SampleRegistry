def test_tags(client):
    response = client.get("/tags")
    print(response.data)
    assert False