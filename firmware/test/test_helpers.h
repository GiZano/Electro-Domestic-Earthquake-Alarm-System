#include <print>

inline int& testFailures() {
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
