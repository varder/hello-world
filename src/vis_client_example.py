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

import time
import logging

import requests

from aos_vis_client import VISClient, VISDataSubscription, VISDataAccessor

logger = logging.getLogger(__name__)


VIS_URL = "wss://wwwivi:8088/"

# Go to https://webhook.site/#/ copy and paste server link to HTTP_REQUEST_RECEIVER_URL
HTTP_REQUEST_RECEIVER_URL = "<replace with your url>"

DATA_SENDING_DELAY = 2
WAIT_TIMEOUT = 5
DELAY_AFTER_ERROR = 2


def main():
    with VISClient(VIS_URL) as client:
        # Initialize data accessor to "VIN" attribute and get this attribute.
        vin_accessor = VISDataAccessor(path="Attribute.Vehicle.VehicleIdentification.VIN")
        client.register_vis_data(vin_accessor)
        vin_accessor.send_get_action()
        vin = vin_accessor.get_value(wait_timeout=WAIT_TIMEOUT)

        # Initialize telemetry info subscription.
        telemetry_sub = VISDataSubscription("Signal.Emulator.telemetry.*")
        client.register_vis_data(telemetry_sub)
        telemetry_sub.send_subscribe_action()

        # Send information received from VIS to HTTP server.
        while True:
            try:
                logger.info("Sending telemetry to '{url}'".format(url=HTTP_REQUEST_RECEIVER_URL))
                requests.post(
                    url=HTTP_REQUEST_RECEIVER_URL,
                    json={"vin": vin, "telemetry": telemetry_sub.get_value(wait_timeout=WAIT_TIMEOUT)}
                )

                time.sleep(DATA_SENDING_DELAY)
            except KeyboardInterrupt:
                logger.info("Received Keyboard interrupt. shutting down")
                break
            except Exception as exc:
                logger.error(
                    "Unhandled exception: {exc_name}".format(exc_name=exc.__class__.__name__),
                    exc_info=True
                )
                time.sleep(DELAY_AFTER_ERROR)
                continue


if __name__ == '__main__':
    main()
