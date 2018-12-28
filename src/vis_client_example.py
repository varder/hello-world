#!/usr/bin/env python3
# Copyright (c) 2018 EPAM Systems
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import time
import logging

import requests
from requests.compat import urljoin

from aos_vis_client import VISClient, VISDataSubscription, VISDataAccessor

logger = logging.getLogger(__name__)


VIS_URL = os.getenv("VIS_URL", "wss://wwwivi:8088/")

# Go to https://webhook.site/#/ copy and paste server link to HTTP_REQUEST_RECEIVER_URL
HTTP_REQUEST_RECEIVER_URL = os.getenv("HTTP_REQUEST_RECEIVER_URL")

DATA_SENDING_DELAY = 2
WAIT_TIMEOUT = 5

LATITUDE_RECEIVER_URL = urljoin(HTTP_REQUEST_RECEIVER_URL, "latitude")
TELEMETRY_RECEIVER_URL = urljoin(HTTP_REQUEST_RECEIVER_URL, "telemetry")
VEH_SPEED_RECEIVER_URL = urljoin(HTTP_REQUEST_RECEIVER_URL, "speed_history")


class VISTelemetryCachedSubscription(VISDataSubscription):
    """
    VISSubscription which saves latest results.
    """
    _CACHE_MAX_SIZE = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = []

    def process(self, data):
        super().process(data)
        self._cache.append(
            {
                "time": time.time(),
                "value": data.get("value"),
            }
        )
        if len(self._cache) > self._CACHE_MAX_SIZE:
            self._cache = self._cache[-self._CACHE_MAX_SIZE:]

    def get_cached_results(self):
        return self._cache


def main():
    with VISClient(VIS_URL) as client:
        # Initialize data accessor to "VIN" attribute and get this attribute.
        vin_accessor = VISDataAccessor(path="Attribute.Vehicle.VehicleIdentification.VIN")
        client.register_vis_data(vin_accessor)
        vin_accessor.send_get_action()
        vin = vin_accessor.get_value(wait_timeout=WAIT_TIMEOUT)

        # Initialize latitude subscription.
        latitude_sub = VISDataSubscription("Signal.Emulator.telemetry.lat")
        client.register_vis_data(latitude_sub)
        latitude_sub.send_subscribe_action()

        # Initialize telemetry info subscription.
        telemetry_sub = VISDataSubscription("Signal.Emulator.telemetry.*")
        client.register_vis_data(telemetry_sub)
        telemetry_sub.send_subscribe_action()

        # initialize custom subscription.
        veh_speed_history_sub = VISTelemetryCachedSubscription("Signal.Emulator.telemetry.veh_speed")
        client.register_vis_data(veh_speed_history_sub)
        veh_speed_history_sub.send_subscribe_action()

        # Send information received from VIS to HTTP server.
        while True:
            try:
                logger.info("Sending latitude to '{url}'".format(url=LATITUDE_RECEIVER_URL))
                requests.post(
                    url=LATITUDE_RECEIVER_URL,
                    json={"vin": vin, "latitude": latitude_sub.get_value(wait_timeout=WAIT_TIMEOUT)}
                )

                logger.info("Sending telemetry to '{url}'".format(url=TELEMETRY_RECEIVER_URL))
                requests.post(
                    url=TELEMETRY_RECEIVER_URL,
                    json={"vin": vin, "telemetry": telemetry_sub.get_value(wait_timeout=WAIT_TIMEOUT)}
                )

                logger.info("Sending speed history to '{url}'".format(url=VEH_SPEED_RECEIVER_URL))
                requests.post(
                    url=VEH_SPEED_RECEIVER_URL,
                    json={"vin": vin, "speed_history": veh_speed_history_sub.get_cached_results()}
                )

                time.sleep(DATA_SENDING_DELAY)
            except KeyboardInterrupt:
                logger.info("Received Keyboard interrupt. shutting down")
                break
            except Exception as e:
                logger.error("Unhandled exception: {exc}".format(exc=e))
                break


if __name__ == '__main__':
    main()
