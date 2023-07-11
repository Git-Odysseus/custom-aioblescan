#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#
# This application is an example on how to use aioblescan
#
# Copyright (c) 2017 François Wautier
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies
# or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR
# IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
import sys
import asyncio
import argparse
import re
import json
import aioblescan as aiobs
from aioblescan.plugins import EddyStone
from aioblescan.plugins import RuuviWeather
from aioblescan.plugins import ATCMiThermometer
from aioblescan.plugins import ThermoBeacon
from aioblescan.plugins import Tilt

# start custom code import
import subprocess
import json
from aioblescan.plugins import WinDoor
#end custom code import


# global
opts = None
decoders = []


def check_mac(val):
    try:
        if re.match("[0-9a-f]{2}([-:])[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", val.lower()):
            return val.lower()
    except:
        pass
    raise argparse.ArgumentTypeError("%s is not a MAC address" % val)


def my_process(data):
    global opts

    ev = aiobs.HCI_Event()
    xx = ev.decode(data)
    if opts.mac:
        goon = False
        mac = ev.retrieve("peer")
        for x in mac:
            if x.val in opts.mac:
                goon = True
                break
        if not goon:
            return

    if opts.raw:
        print("Raw data: {}".format(ev.raw_data))
    if decoders:
        if xx:
            if opts.leader:
                # start custom code
                if (leader == "Temperature info"):
                    json_data = format(xx)
                    new_json = json.dumps(json_data)
                    mqtt_json = new_json.replace("'", "\\\\\\\"")
                    subprocess.call(['sh /custom/script/mqtt_pub.sh temp ' + mqtt_json],shell=True)
                if(leader == "Window/Door info"):
                    json_data = format(xx)
                    new_json = json.dumps(json_data)
                    mqtt_json = new_json.replace("'", "\\\\\\\"")
                    subprocess.call(['sh /custom/script/mqtt_pub.sh door ' + mqtt_json],shell=True)
                # end custom code
                else:
				    #uncomment if debugging
                    #print("{}".format(xx))
                break

    else:
        ev.show(0)


async def amain(args=None):
    global opts

    event_loop = asyncio.get_running_loop()

    # First create and configure a raw socket
    mysocket = aiobs.create_bt_socket(opts.device)

    # create a connection with the raw socket
    # This used to work but now requires a STREAM socket.
    # fac=event_loop.create_connection(aiobs.BLEScanRequester,sock=mysocket)
    # Thanks to martensjacobs for this fix
    conn, btctrl = await event_loop._create_connection_transport(
        mysocket, aiobs.BLEScanRequester, None, None
    )
    # Attach your processing
    btctrl.process = my_process
    if opts.advertise:
        command = aiobs.HCI_Cmd_LE_Advertise(enable=False)
        await btctrl.send_command(command)
        command = aiobs.HCI_Cmd_LE_Set_Advertised_Params(
            interval_min=opts.advertise, interval_max=opts.advertise
        )
        await btctrl.send_command(command)
        if opts.url:
            myeddy = EddyStone(param=opts.url)
        else:
            myeddy = EddyStone()
        if opts.txpower:
            myeddy.power = opts.txpower
        command = aiobs.HCI_Cmd_LE_Set_Advertised_Msg(msg=myeddy)
        await btctrl.send_command(command)
        command = aiobs.HCI_Cmd_LE_Advertise(enable=True)
        await btctrl.send_command(command)
    # Probe
    await btctrl.send_scan_request()
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        print("keyboard interrupt")
    finally:
        print("closing event loop")
        # event_loop.run_until_complete(btctrl.stop_scan_request())
        await btctrl.stop_scan_request()
        command = aiobs.HCI_Cmd_LE_Advertise(enable=False)
        await btctrl.send_command(command)
        conn.close()


def main():
    global opts

    parser = argparse.ArgumentParser(description="Track BLE advertised packets")
    parser.add_argument(
        "-e",
        "--eddy",
        action="store_true",
        default=False,
        help="Look specifically for Eddystone messages.",
    )
    parser.add_argument(
        "-m",
        "--mac",
        type=check_mac,
        action="append",
        help="Look for these MAC addresses.",
    )
    parser.add_argument(
        "-r",
        "--ruuvi",
        action="store_true",
        default=False,
        help="Look only for Ruuvi tag Weather station messages",
    )
    parser.add_argument(
        "-A",
        "--atcmi",
        action="store_true",
        default=False,
        help="Look only for ATC_MiThermometer tag messages",
    )
    parser.add_argument(
        "-T",
        "--thermobeacon",
        action="store_true",
        default=False,
        help="Look only for ThermoBeacon messages",
    )
    parser.add_argument(
        "-R",
        "--raw",
        action="store_true",
        default=False,
        help="Also show the raw data.",
    )

    parser.add_argument(
        "-a",
        "--advertise",
        type=int,
        default=0,
        help="Broadcast like an EddyStone Beacon. Set the interval between packet in millisec",
    )
    parser.add_argument(
        "-u",
        "--url",
        type=str,
        default="",
        help="When broadcasting like an EddyStone Beacon, set the url.",
    )
    parser.add_argument(
        "-t",
        "--txpower",
        type=int,
        default=0,
        help="When broadcasting like an EddyStone Beacon, set the Tx power",
    )
    parser.add_argument(
        "-D",
        "--device",
        type=int,
        default=0,
        help="Select the hciX device to use (default 0, i.e. hci0).",
    )
    parser.add_argument(
        "--tilt",
        action="store_true",
        default=False,
        help="Look only for Tilt hydrometer messages",
    )
    parser.add_argument(
        "--skip-leader",
        action="store_false",
        dest="leader",
        help="suppress leading text identifier",
    )
    #parser added for door/window sensor
    parser.add_argument(
        "-W",
        "--windoor",
        action="store_true",
        default=False,
        help="Look only for Mijia Window/Door messages",
    )
    #end parser
	
    try:
        opts = parser.parse_args()
    except Exception as e:
        parser.error("Error: " + str(e))

    if opts.eddy:
        decoders.append(("Google Beacon", EddyStone()))
    if opts.ruuvi:
        decoders.append(("Weather info", RuuviWeather()))
    if opts.atcmi:
        decoders.append(("Temperature info", ATCMiThermometer()))
    if opts.thermobeacon:
        decoders.append(("Temperature info", ThermoBeacon()))
    if opts.tilt:
        decoders.append(("Tilt", Tilt()))
    # start window/door sensor
	if opts.windoor:
        decoders.append(("Window/Door info", WinDoor()))
    # end window/door sensor
		
    try:
        asyncio.run(amain())
    except:
        pass


if __name__ == "__main__":
    main()
