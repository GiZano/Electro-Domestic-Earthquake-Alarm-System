#include <unity.h>
#include <math.h>

void setUp(void) {}
void tearDown(void) {}

static const float HPF_ALPHA = 0.9f;
static const float TRIGGER_RATIO = 1.8f;
static const float NOISE_FLOOR = 0.04f;

static float high_pass_filter(float prev_filtered, float prev_raw, float raw) {
    return HPF_ALPHA * (prev_filtered + raw - prev_raw);
}

void test_hpf_removes_gravity_bias(void) {
    float filtered = 0.0f, prev_raw = 9.81f;
    for (int i = 0; i < 100; i++) {
        filtered = high_pass_filter(filtered, prev_raw, 9.81f);
        prev_raw = 9.81f;
    }
    TEST_ASSERT_FLOAT_WITHIN(0.01, 0.0, filtered);
}

void test_hpf_passes_transient(void) {
    float filtered = 0.0f, prev_raw = 9.81f;
    filtered = high_pass_filter(filtered, prev_raw, 12.0f);
    TEST_ASSERT_TRUE(filtered > 1.0f);
}

void test_noise_floor_clamps_small_signals(void) {
    float abs_signal = 0.01f;
    if (abs_signal < NOISE_FLOOR) abs_signal = 0.0f;
    TEST_ASSERT_FLOAT_WITHIN(0.001, 0.0, abs_signal);

    abs_signal = 0.05f;
    if (abs_signal < NOISE_FLOOR) abs_signal = 0.0f;
    TEST_ASSERT_TRUE(abs_signal > 0.0f);
}

void test_trigger_ratio_detects_event(void) {
    float sta = 0.12f;
    float lta = 0.07f;
    if (lta < 0.01f) lta = 0.01f;
    float ratio = sta / lta;
    TEST_ASSERT_TRUE(ratio >= TRIGGER_RATIO);
}

void test_trigger_ratio_suppresses_noise(void) {
    float sta = 0.04f;
    float lta = 0.04f;
    if (lta < 0.01f) lta = 0.01f;
    float ratio = sta / lta;
    TEST_ASSERT_TRUE(ratio < TRIGGER_RATIO);
}

void test_lta_floor_protects_division_by_zero(void) {
    float lta = 0.0f;
    if (lta < 0.01f) lta = 0.01f;
    float sta = 0.05f;
    float ratio = sta / lta;
    TEST_ASSERT_TRUE(ratio >= 0.0f);
    TEST_ASSERT_FALSE(isinf(ratio));
}

int main(int argc, char **argv) {
    UNITY_BEGIN();

    RUN_TEST(test_hpf_removes_gravity_bias);
    RUN_TEST(test_hpf_passes_transient);
    RUN_TEST(test_noise_floor_clamps_small_signals);
    RUN_TEST(test_trigger_ratio_detects_event);
    RUN_TEST(test_trigger_ratio_suppresses_noise);
    RUN_TEST(test_lta_floor_protects_division_by_zero);

    return UNITY_END();
}
