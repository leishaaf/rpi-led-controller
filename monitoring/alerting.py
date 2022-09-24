import requests
import time

def checkUpStatus():
    response = requests.get("http://192.168.69.143:9090/api/v1/query?query=time()-neel")
    response = json.loads(response.text)
    if(int((response['data']['result'][0]['value'][1]).split(".")[0]) > 40):
        discordMessage("It is Down")
    else:
        print("no need")

def discordMessage(message):
    url = "https://discord.com/api/webhooks/981743754975281212/vDmBiz5f1fV5ZjEWzij35axeio9I6KyjrDHSJehSaXLDnD9ZLhB802UapLp8YxxT_MjU"
    data = {
        "content": "Tunnels Are Down",
        "username": "Neel"
    }
    data["embeds"] = [
        {
            "description": message,
            "title": "Tunnels Down"}]
    response = requests.post(url, json=data)
    if(response.status_code < 400):
        print("Sent Discord Message")
    else:
        print("Error sending Message")

print("Starting")
discordMessage("THIS IS TO LET YOU KNOW THE DISCORD MESSAGE HAS SUCCESFULLY HAS STARTED")
while(True):
    checkUpStatus()
    time.sleep(7200)