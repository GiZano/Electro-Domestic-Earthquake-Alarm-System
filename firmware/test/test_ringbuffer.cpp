#include <cassert>
#include <cmath>
#include <cstdio>
#include <print>
#include "../src/RingBuffer.h"

static int& testFailures() {
    static int count = 0;
    return count;
}

#define CHECK(cond, msg) do { \
    if (!(cond)) { \
        std::print(stderr, "FAIL: {} ({})\n", msg, #cond); \
        testFailures()++; \
    } \
} while(0)

#define CHECK_FLOAT(a, op, b, msg) do { \
    if (!((a) op (b))) { \
        std::print(stderr, "FAIL: {} -- expected {} {} {}\n", msg, (double)(a), #op, (double)(b)); \
        testFailures()++; \
    } \
} while(0)

int main() {
    // New buffer is empty
    {
        RingBuffer<10> buf;
        CHECK(!buf.isFull(), "new buffer not full");
        CHECK_FLOAT(buf.average(), ==, 0.0f, "empty average is zero");
    }

    // Push one value
    {
        RingBuffer<10> buf;
        buf.push(5.0f);
        CHECK(!buf.isFull(), "single push not full");
        CHECK_FLOAT(buf.average(), ==, 5.0f, "single push average");
    }

    // Fill buffer completely
    {
        RingBuffer<10> buf;
        for (int i = 1; i <= 10; i++) buf.push((float)i);
        CHECK(buf.isFull(), "full buffer");
        CHECK_FLOAT(buf.average(), ==, 5.5f, "full buffer average");
    }

    // Uniform values
    {
        RingBuffer<100> buf;
        for (int i = 0; i < 100; i++) buf.push(3.14f);
        CHECK(buf.isFull(), "uniform full");
        CHECK_FLOAT(fabs(buf.average() - 3.14f), <, 0.001f, "uniform average");
    }

    // Wraparound
    {
        RingBuffer<5> buf;
        for (int i = 0; i < 100; i++) buf.push(10.0f);
        CHECK(buf.isFull(), "wrap full");
        CHECK_FLOAT(buf.average(), ==, 10.0f, "wrap average");
    }

    // Overwrite changes average
    {
        RingBuffer<5> buf;
        for (int i = 0; i < 5; i++) buf.push(0.0f);
        CHECK_FLOAT(buf.average(), ==, 0.0f, "zeros average");
        buf.push(50.0f);
        CHECK_FLOAT(buf.average(), ==, 10.0f, "overwrite average");
    }

    if (testFailures() > 0) {
        std::print(stderr, "\n{} test(s) FAILED\n", testFailures());
        return 1;
    }
    printf("All RingBuffer tests PASSED\n");
    return 0;
}
