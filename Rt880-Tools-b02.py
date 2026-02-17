# Source -
# Posted by Balandraud,
# 2025-12-31, License - CC BY-SA 4.0

import sys
import time
import serial
import os
import yaml
import requests
import json


from datetime import datetime
from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection
from huawei_lte_api.enums.client import ResponseEnum
FEND = 0xC0
FESC = 0xDB
TFEND = 0xDC
TFESC = 0xDD

def load_config(filename="config.yaml"):
    with open("config.yaml") as f:
        config = yaml.safe_load(f)
        return config

def encode_kiss(data: bytes) -> bytes:
        encoded = bytearray([FEND, 0x00])  # 0x00 = Data frame on port 0
        for b in data:
            if b == FEND:
                encoded.extend([FESC, TFEND])
            elif b == FESC:
                encoded.extend([FESC, TFESC])
            else:
                encoded.append(b)
        encoded.append(FEND)
        return bytes(encoded)

def decode_kiss( frame: bytes) -> bytes:
        """Remove KISS framing and unescape bytes."""
        print(frame)
        data = bytearray()
        i = 0
        while i < len(frame):
            if frame[i] == FESC:
                i += 1
                if frame[i] == TFEND:
                    data.append(FEND)
                elif frame[i] == TFESC:
                    data.append(FESC)
            else:
                data.append(frame[i])
            i += 1
        return bytes(data)

def ax25_to_aprs(ax25):
        i = 0
        addrs = []
        addrs2 = []
        daprs = []
        while True:
            call = "".join(chr(ax25[i+j] >> 1) for j in range(6)).strip()
            call2 = "".join(chr(ax25[i+j]) for j in range(6)).strip()

            ssid = (ax25[i+6] >> 1) & 0x0F
            addrs.append(f"{call}-{ssid}" if ssid else call)
            addrs2.append(f"{call2}" if ssid else call2)
            last = ax25[i+6] & 0x01
            i += 7
            if last:
                break

        daprs.append(addrs)
        daprs.append(ssid)
        payload = ax25[i+2:].decode("ascii", errors="ignore")
        dpayload=payload.split('}')
        daprs.append(dpayload[0])
        daprs.append(dpayload[1])

        daprs.append(addrs2)

        return daprs


def mic_e_decode(desti, info):
    """
    Decode APRS Mic-E position
    dest : destination callsign (6 chars)
    info : payload string (Mic-E info field)
    """

    if len(desti) != 6 or len(info) < 6:
        raise ValueError("Invalid Mic-E frame")

    # ----- LATITUDE -----
    lat_deg = ""
    lat_min = ""

    for i in range(3):
        c = ord(desti[i])
        if c >= ord('P'):
            lat_deg += str(c - ord('P'))
        else:
            lat_deg += str(c - ord('0'))

    for i in range(3, 6):
        c = ord(desti[i])
        if c >= ord('P'):
            lat_min += str(c - ord('P'))
        else:
            lat_min += str(c - ord('0'))

    latitude = int(lat_deg[:2]) + int(lat_deg[2] + lat_min) / 600.0

    # Hemisphere
    if ord(desti[3]) < ord('P'):
        latitude = -latitude

    # ----- LONGITUDE -----
    lon_deg = ord(info[0]) - 28
    lon_min = ord(info[1]) - 28
    lon_frac = ord(info[2]) - 28

    longitude = lon_deg * 1.0 + (lon_min + lon_frac / 100) / 60

    if ord(info[3]) & 0x20:
        longitude = -longitude

    # ----- SPEED / COURSE -----
    speed = (ord(info[3]) - 28) * 10
    course = (ord(info[4]) - 28) * 4

    return {
        "latitude": round(latitude, 5),
        "longitude": round(longitude, 5),
        "speed_kmh": round(speed * 1.852, 1),
        "course": course
    }

def main():
 cfg=load_config()
 comport = cfg["serial"]["port"]
 bds=cfg["serial"]["speed"]
 f_beacon1 = "AA 30 00 A0 08 00 00"
 Durl= cfg["root"]["url"]
 Dphone_number=cfg["root"]["tel"]
 Dusername=cfg["root"]["user"]
 Dpassword=cfg["root"]["pass"]
 Dtms=cfg["transmitto"]["tsms"]
 Dthas=cfg["transmitto"]["thas"]
 Dcallsign=cfg["rcvcallsign"]["callsign"]
 Dprotocol=cfg["protocol"]
 # configure the serial connections (the parameters differs on the device you are connecting to)
 ser = serial.Serial(
    port=comport,
    baudrate=bds,
    timeout=2
 )

 if ser.isOpen():
       print("Serial port", comport, "has been opened successfully.")
 else:
       print ("Failed to open serial port", comport)
       sys.exit()




 saisie=""
 num=0
 ODlongitude=0
 ODlatitude=0
 Dlongitude=0
 Dlatitude=0

 while 1 :

    num +=1
    if Dprotocol == "rt880":

        frame = bytes.fromhex(f_beacon1)
        ser.write(frame)
        #print (frame)
        out = ''
        # let's wait one second before reading output (let's give device time to answer)
        time.sleep(1)
        out = ser.read(135)
        slong = len(out)
        #print(out)
        if slong == 135:
            dt = datetime.now()
            ts = datetime.timestamp(dt)

            clong = out[106:110]
            clati = out[94:98]
            slongitude = out[111:112]
            slatitude = out[99:100]
            Dlongitude = int.from_bytes(clong, "little") / 100000
            Dlatitude = int.from_bytes(clati, "little") / 100000
            Bsour = out[29:38]
            Bsour= Bsour[0:Bsour.find(0x00)]
            rcallsign= str(Bsour[0:Bsour.find(0x2D)], 'utf-8')

            Bmess = out[40:64]
            Bmess= Bmess[0:Bmess.find(0x00)]

    if Dprotocol == "kiss":
            print ("Kiss Mode")
            out = ser.read_until(bytes([FEND]))
            #print (out)

            if out and out[0] == 0X00:

                parts = out.split(bytes([FEND]))
                #print(parts)
                for p in parts:
                    if p and p[0] == 0x00:
                        bout=decode_kiss(p[1:])
                        print (bout)

                mice= ax25_to_aprs (bout)
                print (mice)
                print (mice[2])
                print (mic_e_decode(mice[4][1], mice[2]))

    if (ODlatitude!=Dlatitude or ODlongitude!=Dlongitude) and (Dlongitude!=0 and Dlatitude!=0) and (rcallsign in Dcallsign):

                print ("--------------------------------------")
                print(num)
                #print (rcallsign)
                print ("--------------------------------------")
                print ("Source :",str(Bsour, encoding='utf-8'))
                print ("Message :",str(Bmess, encoding='utf-8',errors="ignore"))
                print (Dlatitude,str(slatitude, encoding='utf-8')," ",Dlongitude,str(slongitude, encoding='utf-8'))
                print ("--------------------------------------")



                ODlatitude=Dlatitude
                ODlongitude=Dlongitude
                Dmessage="De : "+str(Bsour,encoding='ascii')+" Message :"+str(Bmess,encoding='ascii')+"\r"
                Dmessage=Dmessage+"Latitude : "+str(Dlatitude)+ str(slatitude,encoding='ascii')+" Longitude : "+str(Dlongitude)+str(slatitude,encoding='ascii')+"\r"
                Dmessage=Dmessage+"http://maps.google.com?q="+str(Dlatitude)+ str(slatitude,encoding='ascii')+","+str(Dlongitude)+str(slongitude,encoding='ascii')+"\r"

                if Dtms:
                    print ("Sms")
                    with Connection(Durl, username=Dusername, password=Dpassword) as connection:
                        client = Client(connection)
                        if client.sms.send_sms([Dphone_number[0]], Dmessage) == ResponseEnum.OK.value:
                          print("✔ SMS was send successfully")
                        else:
                          print("❌ Error")
                    print ("--------------------------------------")
                if Dthas:
                    print ("Home Assistant")

                    URL_HA = cfg["has"]["urlha"]
                    ENTITY_ID = cfg["has"]["entityid"]+rcallsign
                    HA_TOKEN = cfg["has"]["hatoken"]

                    altitude = 35        # optionnel

                    # ===== REQUETE =====
                    url = f"{URL_HA}/api/states/{ENTITY_ID}"
                    headers = {
                        "Authorization": f"Bearer {HA_TOKEN}",
                        "Content-Type": "application/json"
                    }

                    data = {
                        "state": "not_home",  # ou "not_home" etc.
                        "attributes": {
                            "latitude": Dlatitude,
                            "longitude": Dlongitude,
                            "gps_accuracy": 10,
                            "altitude": altitude
                        }
                    }

                    response = requests.post(url, headers=headers, data=json.dumps(data))

                    if response.status_code in [200, 201]:
                        print("✔ Coordonnées envoyées ! Pour : ",rcallsign)
                    else:
                        print("❌ Erreur:", response.status_code, response.text)











    #time.sleep(1)

if __name__ == "__main__":
    main()
