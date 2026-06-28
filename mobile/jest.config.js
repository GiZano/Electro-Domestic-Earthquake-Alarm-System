module.exports = {
  preset: "jest-expo",
  transformIgnorePatterns: [
    "node_modules/(?!((jest-)?react-native|@react-native(-community)?)|expo(nent)?|@expo(nent)?/.*|zustand|@tanstack/react-query|victory-native)/",
  ],
  moduleFileExtensions: ["ts", "tsx", "js", "jsx"],
};
