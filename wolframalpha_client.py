from wolframalpha import Client
import os

# Replace the app_id variable with your own App ID from the Wolfram|Alpha Developer Portal
app_id = os.environ.get("WolframAlpha-App-ID")

# Create a client object with the app_id
client = Client(app_id)

async def query_wolfram(query):
    # Send the query to Wolfram|Alpha and get the response
    res = client.query(query)
    try:
        if res["didyoumeans"] is not None:
            print(res["didyoumeans"])
            query = " ".join(x["#text"] for x in res["didyoumeans"]["didyoumean"])
            res = client.query(query)
    except:
        pass
    # Extract the plaintext result from the response
    try:
        res = next(res.results)
        if res.text is not None:
            return res.text
        else:
            return res.subpod.img.src
    except:
        return None   
