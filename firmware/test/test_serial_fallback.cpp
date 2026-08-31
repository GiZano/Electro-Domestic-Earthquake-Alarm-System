#include <cstdio>
#include <string>
#include "test_helpers.h"
#include "../src/SerialFallback.h"

int main() {
    // Frame format must mirror the MQTT data-plane payload exactly
    {
        std::string frame = buildSerialFrame("[QG:FB]", 250, 42, 1720000000L,
                                             "0123456789abcdef0123456789abcdef");
        std::string expected =
            R"([QG:FB]{"value":250,"sensor_id":42,"device_timestamp":1720000000,"signature_hex":"0123456789abcdef0123456789abcdef"})";
        CHECK(frame == expected, "serial frame matches MQTT payload layout");
    }

    // Negative values (ADXL345 vibration) must be preserved
    {
        std::string frame = buildSerialFrame("[QG:FB]", -8192, 7, 1700000000L, "sig");
        CHECK(frame == R"([QG:FB]{"value":-8192,"sensor_id":7,"device_timestamp":1700000000,"signature_hex":"sig"})",
              "negative value survives the frame builder");
    }

    // Routing decision
    {
        CHECK(decidePath(true, false, false) == DeliveryPath::MQTT,
              "MQTT wins whenever the broker is reachable");
        CHECK(decidePath(false, true, true) == DeliveryPath::SERIAL_CDC,
              "serial fallback needs host + valid time");
        CHECK(decidePath(false, true, false) == DeliveryPath::RETAIN,
              "no serial frames before NTP time is valid");
        CHECK(decidePath(false, false, true) == DeliveryPath::RETAIN,
              "no host present -> retain instead of writing to a dead port");
    }

    // Retention ring is FIFO and bounded
    {
        RetentionRing<4> ring;
        CHECK(ring.empty(), "fresh ring is empty");

        ring.push({1, 100L});
        ring.push({2, 200L});
        ring.push({3, 300L});

        SerialEvent evt;
        CHECK(ring.pop(evt) && evt.value == 1, "FIFO pop returns oldest first");
        CHECK(ring.pop(evt) && evt.value == 2, "FIFO order preserved");
        CHECK(ring.pop(evt) && evt.value == 3, "FIFO order preserved (last)");
        CHECK(ring.empty(), "ring drains fully");

        CHECK(!ring.pop(evt), "pop on empty ring fails");
    }

    // Overwrite oldest when full
    {
        RetentionRing<3> ring;
        for (int i = 1; i <= 5; i++) ring.push({i, (long)i});
        CHECK(ring.size() == 3, "ring capacity is bounded");

        SerialEvent evt;
        CHECK(ring.pop(evt) && evt.value == 3, "oldest overwritten entries are dropped");
        CHECK(ring.pop(evt) && evt.value == 4, "FIFO after wraparound");
        CHECK(ring.pop(evt) && evt.value == 5, "most recent survives");
    }

    if (testFailures() > 0) {
        fprintf(stderr, "\n%d test(s) FAILED\n", testFailures()); // NOSONAR(cpp:S6494)
        return 1;
    }
    printf("All serial fallback tests PASSED\n"); // NOSONAR(cpp:S6494)
    return 0;
}
