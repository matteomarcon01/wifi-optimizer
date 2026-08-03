# Wi-Fi diagnosis guide

Use this guide only for the read-only diagnosis function. Produce evidence and a likely problem layer without changing router or client settings.

## 1. Define the symptom and scope

Determine, through safe inspection or one concise question:

- Which devices, locations, and applications are affected.
- Whether one service, one device, Wi-Fi devices, or every connection is affected.
- Whether an ISP gateway, separate router, mesh nodes, extenders, VPN, proxy, or private relay is involved.
- Whether the user prioritizes stability, range, latency, or maximum throughput.

Do not block safe read-only inspection on details that can be discovered.

## 2. Capture a layered baseline

1. Identify the active interface and default gateway without collecting saved credentials or scanning unrelated networks.
2. Send 30-100 probes to the local gateway. Record loss, average or median latency, maximum latency, and jitter.
3. Test small HTTPS requests over IPv4 and IPv6 against at least two independent endpoints. A failed public ICMP ping alone does not prove the internet is down.
4. When available, measure unloaded and loaded latency with a platform network-quality or bufferbloat test.
5. Record the affected device's band, approximate signal quality, roaming or disconnect behavior, and the time of a real buffering event.

Use `scripts/network_probe.py` when Python and basic network tools are available. Pass `--gateway` if automatic detection fails. Prefer the bundled public HTTPS endpoints and never pass credentials or secret URL components.

## 3. Inspect the router read-only

Read only the values required for diagnosis:

- Router model, firmware version, operating mode, and WAN topology.
- Enabled radios, SSID arrangement, guest networks, and mesh or extender topology.
- Channel, channel width, transmit-power mode, band steering, MLO, Wi-Fi generation or compatibility mode, and TWT.
- Connected-device count and the affected device's band and approximate signal quality.
- QoS or SQM state and configured upload/download rates.
- IPv4 and IPv6 status without reporting addresses.

Check firmware availability read-only. Do not reveal password fields exposed by the page.

## 4. Classify the likely layer

| Observation | Likely layer | Next check | Avoid |
| --- | --- | --- | --- |
| Local-gateway loss or repeated idle spikes | Radio interference, weak signal, roaming, driver, or access-point load | Compare near/far, bands, channels, widths, and another client | Blaming the ISP first |
| Local gateway is clean; HTTPS stalls across services | WAN, ISP, upstream routing, DNS, or protocol path | Compare Ethernet, WAN status, IPv4, IPv6, and ISP gateway | Repeated Wi-Fi channel changes |
| Only one device stalls | Client radio, power saving, VPN, application, codec, or private relay | Test another app and device at the same location | Reconfiguring every client |
| Only one video service stalls | Application or CDN path | Compare web/app playback and another network | Treating a speed test as proof |
| Latency rises only under upload/download | Bufferbloat or saturation | Measure sustainable rates and loaded latency in each direction | Enabling QoS with guessed rates |
| Stalls coincide with roaming or band changes | Coverage, mesh, steering, or MLO | Inspect band/node association and signal near the event | Splitting SSIDs before confirming |
| IPv6 repeatedly fails while IPv4 works across endpoints | IPv6 path or router-advertisement issue | Recheck after reconnect, compare Ethernet, and propose a temporary A/B test | Disabling IPv6 after one failure |
| Synthetic tests pass but playback still stalls | Intermittent radio event, application/CDN behavior, or insufficient observation time | Monitor during a real event | Declaring the issue solved immediately |

Apply these evidence rules:

- Account for routers that deprioritize ICMP before treating gateway loss as conclusive.
- Investigate the client, application, VPN, codec, or CDN first when only one device or service is affected.
- Suspect bufferbloat only when latency rises repeatedly under load.
- Require timing correlation before attributing a stall to roaming, steering, mesh, or MLO.
- Verify SSID and BSSID evidence before claiming that access points duplicate a network.
- Require repeated IPv6-only failure across independent endpoints before proposing an A/B test.
- Never treat high throughput as proof of stability or one observation as proof of root cause.

## 5. Report and hand off

Report the likely layer, confidence, supporting and contradicting evidence, and the smallest next test. Label all setting ideas as proposals and explicitly state that no settings were changed.

Use at least 30 local probes; 50-100 is better for intermittent jitter. Compare average or median latency with worst-case latency, compare Ethernet when possible, and validate with the original application long enough to cover its normal failure interval.
