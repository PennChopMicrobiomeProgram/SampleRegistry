def test_request_example(client):
    response = client.post("/download/1.tsv")
    # Print all attributes of response
    print(dir(response))
    print(response.stream.mode)
    # werkzeug.wrappers.response.ResponseStream
    # Read the response stream
    
    with open("1.tsv", "rb") as f:
        expected_response = f.read()
    assert b"<h2>Hello, World!</h2>" in expected_response