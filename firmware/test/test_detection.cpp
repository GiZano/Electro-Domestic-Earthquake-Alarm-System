#include <cassert>
#include <cmath>
#include <cstdio>

static int& testFailures() {
    static int count = 0;
    return count;
}

#define CHECK(cond, msg) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s (%s)\n", msg, #cond); \
        testFailures()++; \
    } \
} while(0)

#define CHECK_FLOAT(a, op, b, msg) do { \
    if (!((a) op (b))) { \
        fprintf(stderr, "FAIL: %s -- expected %f %s %f\n", msg, (double)(a), #op, (double)(b)); \
        testFailures()++; \
    } \
} while(0)

static const float HPF_ALPHA = 0.9f;
static const float TRIGGER_RATIO = 1.8f;
static const float NOISE_FLOOR = 0.04f;

static float high_pass_filter(float prev_filtered, float prev_raw, float raw) {
    return HPF_ALPHA * (prev_filtered + raw - prev_raw);
}

int main() {
    // HPF removes gravity bias
    {
        float filtered = 0.0f, prev_raw = 9.81f;
        for (int i = 0; i < 100; i++) {
            filtered = high_pass_filter(filtered, prev_raw, 9.81f);
            prev_raw = 9.81f;
        }
        CHECK_FLOAT(fabs(filtered), <, 0.01f, "HPF removes gravity");
    }

    // HPF passes transients
    {
        float filtered = 0.0f, prev_raw = 9.81f;
        filtered = high_pass_filter(filtered, prev_raw, 12.0f);
        CHECK(filtered > 1.0f, "HPF passes transient");
    }

    // Noise floor clamps small signals
    {
        float signal = 0.01f;
        if (signal < NOISE_FLOOR) signal = 0.0f;
        CHECK_FLOAT(signal, ==, 0.0f, "noise floor clamps");

        signal = 0.05f;
        if (signal < NOISE_FLOOR) signal = 0.0f;
        CHECK(signal > 0.0f, "above noise floor passes");
    }

    // Trigger ratio detects earthquake
    {
        float sta = 0.13f, lta = 0.07f;
        if (lta < 0.01f) lta = 0.01f;
        float ratio = sta / lta;
        CHECK(ratio >= TRIGGER_RATIO, "STA/LTA triggers on quake");
    }

    // Trigger ratio suppresses noise
    {
        float sta = 0.04f, lta = 0.04f;
        if (lta < 0.01f) lta = 0.01f;
        float ratio = sta / lta;
        CHECK(ratio < TRIGGER_RATIO, "STA/LTA suppresses noise");
    }

    // LTA floor protects division by zero
    {
        float lta = 0.0f;
        if (lta < 0.01f) lta = 0.01f;
        float ratio = 0.05f / lta;
        CHECK(ratio >= 0.0f, "LTA floor positive");
        CHECK(!std::isinf(ratio), "LTA floor no infinity");
    }

    if (testFailures() > 0) {
        fprintf(stderr, "\n%d test(s) FAILED\n", testFailures());
        return 1;
    }
    printf("All detection tests PASSED\n");
    return 0;
}
