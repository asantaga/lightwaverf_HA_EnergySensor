import socket
import logging
import json


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', 9761))
sock.settimeout(20.0) # Wait a Max of 10 seconds
# wait for an energy update
data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
lightwaveEnergyDataRaw=data[2:]
lwrfJson=json.loads(lightwaveEnergyDataRaw)
print("LWEnergy Raw {}".format(lwrfJson))
print("LW cUse value = {}".format(lwrfJson.get("cUse")))
todUse=lwrfJson.get("todUse")
i=todUse/1000
print("LW todUse value = {}".format(i))
