#!/usr/bin/env python3 -*- coding:utf-8 -*-
#
# This file deals with Xiaomi Mijia Door/Window formatted messages

from .ble_parser import BleParser

#device key pair
WINDOR_DEVICE_KEY = {
   "e4aaec6917a3": "3c9c63d7e297e978266f8541b92f4865",
}

def parse(self, packet):
    peer = packet.retrieve("peer")
    rssi = packet.retrieve("rssi")
    svc_data = packet.retrieve("Service Data uuid")
    adv_payload = packet.retrieve("Adv Payload")
    if peer and rssi and svc_data and adv_payload:
        mac = peer[0].val
        uuid = svc_data[0].val
        if b"\xfe\x95" == uuid:
            #get raw data from packet
            data = packet.raw_data
            adv_payload_str = ":".join("%02x" % x for x in adv_payload[0].val)
            adv_payload_rev = adv_payload_str.split(":")
            adv_payload_fixed = ":".join(reversed(adv_payload_rev))
            mac_in_payload = ":".join("%02x" % x for x in adv_payload[0].val[5:11])
            mac_in_rev = ":".join(reversed([mac_in_payload[i:i+3] for i in range(0, len(mac_in_payload), 3)]))
            mac_address = mac_in_rev.replace(":", "")
            return run_ble_monitor(self, data, mac_address)

def run_ble_monitor(self, data, mac):
    self.aeskeys = {}
    ble_key = WINDOR_DEVICE_KEY[mac]
    p_key = bytes.fromhex(ble_key.lower())
    p_mac = bytes.fromhex(mac)
    self.aeskeys[p_mac] = p_key
    ble_parser = BleParser(report_unknown=False,
        discovery=True,
        filter_duplicates=True,
        sensor_whitelist=None,
        tracker_whitelist=None,
        report_unknown_whitelist=None,
        aeskeys=self.aeskeys)
    sensor_msg, tracker_msg = ble_parser.parse_raw_data(data)

	#add values of attributes if they are part of the msg, else use "N/A"
    if isinstance(sensor_msg, dict):
        if "light" in sensor_msg:
            light = sensor_msg["light"]
        else:
            light = "N/A"
        if "status" in sensor_msg:
           state = sensor_msg["status"]
        else:
           state = "N/A"
        if "battery" in sensor_msg:
           battery = sensor_msg["battery"]
        else:
           battery = "N/A"
        if "illuminance" in sensor_msg:
           illuminance = sensor_msg["illuminance"]
        else:
           illuminance = "N/A"
    else:
        return {}

    return {
               "mac_address": sensor_msg["mac"],
               "state": state,
               "light": light,
               "illuminance": illuminance,
               "battery": battery,
               "rssi": sensor_msg["rssi"],
           }

class WinDoor(object):
    """Class defining the content of an Xiaomi Mijia Door/Window advertisement."""

    def decode (self, packet):
        # Look for Xiaomi Mijia Door/Window custom firmware advertisements
        result = parse(self, packet)

        return result
