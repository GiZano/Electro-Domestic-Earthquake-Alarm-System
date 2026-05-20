#pragma once

template <size_t S>
class RingBuffer {
private:
    float buffer[S] = {0};
    size_t head = 0;
    size_t count = 0;
    float sum = 0;

public:
    // Push a new value into the buffer, overwriting the oldest value
    void push(float val) {
        sum -= buffer[head];      // Remove the oldest value from the running sum
        buffer[head] = val;       // Insert the new value
        sum += val;               // Add the new value to the running sum
        
        head = (head + 1) % S;    // Advance the head pointer, wrapping via modulo
        
        if (count < S) count++;   // Track how many items we actually have
    }

    // O(1) Average calculation based on the running sum
    float average() const {
        if (count == 0) return 0.0f;
        return sum / count;
    }

    // Check if the buffer has completely filled up its window
    bool isFull() const { 
        return count == S; 
    }
};