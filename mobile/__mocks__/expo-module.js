module.exports = {
  __esModule: true,
  default: {},
  setNotificationHandler: jest.fn(),
  scheduleNotificationAsync: jest.fn(),
  requestPermissionsAsync: jest.fn().mockResolvedValue({ status: "granted" }),
  getPermissionsAsync: jest.fn().mockResolvedValue({ status: "granted" }),
  setNotificationChannelAsync: jest.fn(),
  isDevice: false,
  AndroidImportance: { MAX: 5 },
  AndroidNotificationPriority: { MAX: 5 },
};
