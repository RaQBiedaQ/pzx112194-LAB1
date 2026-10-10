<!-- ai-generated: 35% - the assistant drafted the explanation from the student's own measured numbers; the student ran the measurement and reviewed the arithmetic against the toxic's parameters. -->

# The client-server gap, with a known toxic in front of svcdesk

We put Toxiproxy (2.12.0) between the load generator and `svcdesk`, with a single latency toxic on the
downstream (response) stream, applied to 100% of traffic: `{"type": "latency", "latency": 100,
"jitter": 10}` (milliseconds). We then ran the same M-08 measurement (`itsmlab load 3`) through the
proxy's published port instead of directly at `svcdesk`.

`client_p99_seconds` is oha's own p99 over that run, measured from outside the proxy: 275.6 ms.
`server_p99_seconds` is our own request histogram's p99 over the same run, read from `svcdesk`'s
`/metrics` (`histogram_quantile(0.99, ...)` over the bucket increments) - 170.8 ms, essentially
identical to our baseline measurement without the proxy at all (170.9-177.8 ms across earlier runs).
`gap_seconds` is the difference: 104.8 ms.

That the gap (104.8 ms) sits close to the toxic's own declared latency (100 ms, plus up to 10 ms of
jitter) is exactly the point, and it is not a coincidence: the toxic adds a fixed extra delay to every
response on its way back through the proxy, entirely *after* `svcdesk` has already finished handling
the request and its own histogram has already recorded the observation. `svcdesk`'s histogram times
only the work `svcdesk` itself does - receiving the request, calling `kb-index`, building the response -
and that work is wholly unaware that Toxiproxy exists on the wire between it and the client. The
client's p99, by contrast, is a measurement of the whole round trip as an outside caller experiences it,
and so it necessarily includes every millisecond the toxic injects on top.

This is the general shape of any gap between a server-side RED histogram and a client-side latency
measurement in production: a server's own instrumentation can only ever report on the portion of the
request lifecycle that happens inside the server's own process. A load balancer queueing a connection
before forwarding it, a slow TLS handshake, a congested network hop, a sidecar proxy doing its own
buffering, or - as staged here - a deliberately injected network toxic, all add real, user-visible
latency that never touches the server's own clock. A dashboard built only from `svcdesk`'s histogram
would have reported a healthy p99 of 171 ms throughout this entire experiment, even while users (or, in
this synthetic case, the measuring client) actually experienced p99s above 275 ms - a gap large enough,
on its own, to blow through the 200 ms latency threshold declared in `slo.md`. That is the practical
reason a production SLO should be anchored to a client-observed or edge-observed measurement wherever
one is available, with the server-side histogram kept as a second signal for localizing *where* a
regression originates once the client-side SLO has already said that one exists.
