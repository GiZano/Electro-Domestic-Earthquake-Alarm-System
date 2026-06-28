#include <unity.h>
#include "../src/RingBuffer.h"

void setUp(void) {}
void tearDown(void) {}

void test_ringbuffer_new_is_empty(void) {
    RingBuffer<10> buf;
    TEST_ASSERT_FALSE(buf.isFull());
    TEST_ASSERT_FLOAT_WITHIN(0.001, 0.0, buf.average());
}

void test_ringbuffer_push_one_value(void) {
    RingBuffer<10> buf;
    buf.push(5.0f);
    TEST_ASSERT_FALSE(buf.isFull());
    TEST_ASSERT_FLOAT_WITHIN(0.001, 5.0, buf.average());
}

void test_ringbuffer_push_multiple(void) {
    RingBuffer<10> buf;
    for (int i = 1; i <= 10; i++) {
        buf.push((float)i);
    }
    TEST_ASSERT_TRUE(buf.isFull());
    TEST_ASSERT_FLOAT_WITHIN(0.001, 5.5, buf.average());
}

void test_ringbuffer_average_of_identical(void) {
    RingBuffer<100> buf;
    for (int i = 0; i < 100; i++) {
        buf.push(3.14f);
    }
    TEST_ASSERT_TRUE(buf.isFull());
    TEST_ASSERT_FLOAT_WITHIN(0.001, 3.14, buf.average());
}

void test_ringbuffer_wraparound(void) {
    RingBuffer<5> buf;
    for (int i = 0; i < 100; i++) {
        buf.push(10.0f);
    }
    TEST_ASSERT_TRUE(buf.isFull());
    TEST_ASSERT_FLOAT_WITHIN(0.001, 10.0, buf.average());
}

void test_ringbuffer_overwrite_updates_average(void) {
    RingBuffer<5> buf;
    for (int i = 0; i < 5; i++) {
        buf.push(0.0f);
    }
    TEST_ASSERT_FLOAT_WITHIN(0.001, 0.0, buf.average());

    buf.push(50.0f);
    TEST_ASSERT_FLOAT_WITHIN(0.001, 10.0, buf.average());
}

int main(int argc, char **argv) {
    UNITY_BEGIN();

    RUN_TEST(test_ringbuffer_new_is_empty);
    RUN_TEST(test_ringbuffer_push_one_value);
    RUN_TEST(test_ringbuffer_push_multiple);
    RUN_TEST(test_ringbuffer_average_of_identical);
    RUN_TEST(test_ringbuffer_wraparound);
    RUN_TEST(test_ringbuffer_overwrite_updates_average);

    return UNITY_END();
}
