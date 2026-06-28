/* global jest */
module.exports = {
  Vibration: {
    vibrate: jest.fn(),
  },
  Platform: {
    OS: "web",
    select: jest.fn(),
  },
};
