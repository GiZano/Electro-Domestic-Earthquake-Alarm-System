#include <cstdio>

inline int& testFailures() {
    static int count = 0;
    return count;
}

#define CHECK(cond, msg) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s (%s)\n", msg, #cond); /* NOSONAR(cpp:S6494) */ \
        testFailures()++; \
    } \
} while(0)

#define CHECK_FLOAT(a, op, b, msg) do { \
    if (!((a) op (b))) { \
        fprintf(stderr, "FAIL: %s -- expected %f %s %f\n", msg, (double)(a), #op, (double)(b)); /* NOSONAR(cpp:S6494) */ \
        testFailures()++; \
    } \
} while(0)
