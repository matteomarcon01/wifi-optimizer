# Wi-Fi optimization guide

Use this guide only after current diagnosis evidence supports a Wi-Fi or congestion change and the user has authorized optimization.

## 1. Confirm prerequisites

Before changing a setting, ensure that:

- A current baseline and plausible cause exist.
- The change tests that cause rather than applying a generic tweak list.
- The user authorized the change.
- The current value and exact rollback value are recorded.
- The expected benefit, tradeoff, and possible disconnection are explained.
- A management path remains available after a radio restart.

Return to diagnosis if any prerequisite is missing.

## 2. Choose one evidence-backed change group

| Evidence | Candidate test | Main tradeoff | Rollback |
| --- | --- | --- | --- |
| Unstable 2.4 GHz coexistence or wide-channel interference | Use 20 MHz and select a legal channel from a local scan | Lower peak throughput | Restore prior width and channel |
| 5 GHz instability associated with 160 MHz or DFS events | Test 80 MHz or a legal, relatively quiet non-DFS channel | Lower peak throughput | Restore prior width and channel mode |
| Instability limited to Wi-Fi 7 or multi-link clients | Test MLO off | Lower aggregate peak speed | Re-enable MLO |
| A device repeatedly chooses a weak band or roams during stalls | Tune steering or temporarily split band names | Manual band management and reconnects | Restore the combined SSID and steering value |
| Loaded latency rises sharply while throughput saturates | Enable SQM or correctly configured QoS at measured limits | Some throughput reduction | Restore prior QoS state and rates |
| Repeatable IPv6-only failures across independent endpoints | Run a time-bounded IPv6 A/B test | Temporary loss of IPv6 connectivity | Restore IPv6 immediately after the test |
| Strong client signal but weak mesh backhaul | Improve node placement or backhaul before radio tuning | Placement or cabling effort | Restore node placement if worse |

Change only one reversible setting group at a time.

## 3. Apply radio and feature guidance

### 2.4 GHz

- Prefer 20 MHz when stability and coexistence matter.
- Select channels using a local scan and regional rules. Channels 1, 6, and 11 are common planning choices where legal, but are not automatically least congested.
- Use 2.4 GHz for reach and compatibility rather than peak throughput.

### 5 and 6 GHz

- Prefer 80 MHz as a stability test when 160 MHz or DFS behavior is implicated.
- Test a legal non-DFS channel only when radar events, automatic changes, or interference are plausible.
- Check regional support before using upper channels such as 149-161. Never publish a universal channel recommendation.
- Keep automatic channel selection when the router's scan is trustworthy and no channel-change evidence exists.
- Verify local regulatory support for 6 GHz and do not force distant clients onto it.

### Steering, mesh, MLO, compatibility, and TWT

- Keep steering enabled when association is stable. Split band names only when a device repeatedly chooses a weak band or roams at the wrong time.
- Check both client-to-node and mesh-backhaul quality; a strong client signal cannot compensate for weak backhaul.
- Keep the newest stable Wi-Fi generation enabled. Disable MLO only as a reversible compatibility test for affected Wi-Fi 7 clients.
- Use legacy compatibility mode only when a client cannot discover or maintain a connection. Test TWT off only for older-client or sleep/wake evidence.

### QoS, DNS, IPv6, and power

- Use QoS or SQM only with congestion evidence. Measure each direction, begin around 85-95% of sustainable throughput, and re-test loaded latency and throughput.
- Change DNS only when lookup latency, failure, or filtering is demonstrated.
- Keep IPv6 enabled unless repeatable, multi-endpoint evidence supports a time-bounded A/B test; restore it if the test does not help.
- Do not assume maximum transmit power is best. Change it only with coverage and roaming evidence.

## 4. Apply safely

1. Capture a sanitized pre-change record.
2. Use visible, uniquely identified controls; never guess hidden endpoints or undocumented APIs.
3. Save one setting group and accept only the confirmation dialogs required for that change.
4. Expect a browser disconnect during a radio restart and ask the user to reconnect if the wrong saved network is selected.
5. Reload the page and verify server-persisted values.
6. Roll back immediately if reachability is lost and a safe management path remains.

## 5. Verify, keep, or roll back

- Repeat the same gateway, HTTPS, loaded-latency, and original-workload checks used for diagnosis.
- Confirm affected devices reconnected to the intended band or node.
- For intermittent buffering, reproduce the workload for 20-30 minutes.
- Keep the change only when the target symptom improves materially without an unacceptable regression.
- Otherwise restore the recorded value before testing another hypothesis.

Report the exact changed and unchanged values, before/after evidence, tradeoffs, rollback values, and the next diagnostic layer if the symptom returns.
