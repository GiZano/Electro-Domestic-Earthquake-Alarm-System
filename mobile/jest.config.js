module.exports = {
  testEnvironment: "node",
  transform: {
    "^.+\\.tsx?$": ["ts-jest", { tsconfig: "tsconfig.json" }],
  },
  moduleFileExtensions: ["ts", "tsx", "js", "jsx"],
  moduleNameMapper: {
    "^react-native$": "<rootDir>/__mocks__/react-native.js",
    "^expo-notifications$": "<rootDir>/__mocks__/expo-module.js",
    "^expo-device$": "<rootDir>/__mocks__/expo-module.js",
    "^expo-constants$": "<rootDir>/__mocks__/expo-module.js",
    "^expo-font$": "<rootDir>/__mocks__/expo-module.js",
    "^expo-linking$": "<rootDir>/__mocks__/expo-module.js",
    "^expo-splash-screen$": "<rootDir>/__mocks__/expo-module.js",
    "^expo-status-bar$": "<rootDir>/__mocks__/expo-module.js",
    "^expo-web-browser$": "<rootDir>/__mocks__/expo-module.js",
    "^expo-router$": "<rootDir>/__mocks__/expo-module.js",
  },
};
